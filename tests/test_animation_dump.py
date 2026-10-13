import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import animation_dump as animation
from tools import project_index as project


def active_data(images=(2, 5, 5)):
    prefix = bytes(42) + b"SPRI" + struct.pack("<H", 2)
    # Two animation slots and two direction slots deliberately alias their records.
    region = bytearray(36 + 3 + 64 + 8 + 2 * len(images))
    struct.pack_into("<HH16H", region, 0, len(region), 0x1234, *([39, 39] + [0xFFFF] * 14))
    region[36:39] = b"gap"
    struct.pack_into("<32H", region, 39, *([64, 0xFFFF, 64] + [0x8000] * 29))
    region[103:109] = bytes([0, 255, 12, 34, 56, 78])
    struct.pack_into("<H", region, 109, len(images))
    struct.pack_into(f"<{len(images)}H", region, 111, *images)
    return prefix + region + b"opaque-tail"


def project_bytes(active=None, duplicate_bank=False):
    def block(kind, data):
        return struct.pack("<HI", kind, len(data)) + data
    def obj(kind, flags=0, data=None):
        head = bytearray(68)
        head[38], head[42] = flags, kind
        return bytes(head) + (block(0x8000, data) if data is not None else b"")
    objects = struct.pack("<HH", 3, 0) + obj(2, data=active if active is not None else active_data())
    objects += obj(0xFF) + obj(2, 0x80)
    globals_ = struct.pack("<HH", 1, 0) + obj(2, 0x80, active_data())
    level = bytes(184) + block(0x8002, objects)
    header = bytearray(362)
    header[:4] = b"GAME"
    struct.pack_into("<H", header, 4, 0x0207)
    struct.pack_into("<H", header, 348, 1)
    struct.pack_into("<I", header, 358, len(header) + 6 + 6 + len(globals_))
    bank = bytearray(4 + 6 * 8)
    struct.pack_into("<I", bank, 0, 6)
    for slot in (2, 5):
        struct.pack_into("<II", bank, 4 + slot * 8, len(bank), 1)
        bank += b"x"
    return bytes(header) + block(6, globals_) + block(8, level) + block(10 if duplicate_bank else 0x800A, bank) + (
        block(0x800A, bank) if duplicate_bank else b"")


class AnimationTests(unittest.TestCase):
    def test_slots_aliases_gaps_raw_headers_and_handles(self):
        raw = active_data()
        out = animation.decode_active(raw)
        self.assertEqual(out["raw_hex"], raw.hex())
        self.assertEqual(out["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(out["animation_offset"], 48)
        self.assertEqual(len(out["animations"]), 16)
        self.assertEqual([a["pointer_raw_u16"] for a in out["animations"]], [39, 39] + [65535] * 14)
        self.assertEqual(out["opaque_animation_spans"], [{"offset": 84, "raw_hex": b"gap".hex()}])
        self.assertEqual(out["tail_hex"], b"opaque-tail".hex())
        for a in out["animations"][:2]:
            self.assertEqual(a["offset"], 87)
            self.assertEqual(len(a["directions"]), 32)
            self.assertEqual(a["directions"][0]["image_ids"], [2, 5, 5])
            self.assertEqual(a["directions"][2]["image_ids"], [2, 5, 5])
            self.assertEqual(a["directions"][0]["header_hex"], "00ff0c22384e0300")
            self.assertIsNone(a["directions"][1]["image_ids"])
        self.assertIsNone(out["animations"][2]["directions"])

    def test_empty_region_and_zero_frames_remain_distinct_from_absent(self):
        out = animation.decode_active(active_data(()))
        self.assertEqual(out["animations"][0]["directions"][0]["image_ids"], [])
        raw = bytearray(active_data())
        struct.pack_into("<16H", raw, 52, *([65535] * 16))
        out = animation.decode_active(raw)
        self.assertTrue(all(a["directions"] is None for a in out["animations"]))
        self.assertEqual(bytes.fromhex(out["raw_hex"]), raw)
        self.assertEqual(len(out["opaque_animation_spans"]), 1)

    def test_bad_signature_lengths_pointers_counts_and_overlap(self):
        raw = active_data()
        bad = [b"", raw[:47], raw[:42] + b"NOPE" + raw[46:]]
        for offset, value in [(46, 1), (46, 65535), (48, 35), (48, 65535),
                              (52, 35), (52, 32767), (87, 63), (87, 32767),
                              (157, 65535), (89, 66)]:
            changed = bytearray(raw)
            struct.pack_into("<H", changed, offset, value)
            bad.append(changed)
        for data in bad:
            with self.subTest(head=data[:56]):
                with self.assertRaises(project.InputError):
                    animation.decode_active(data)

        partial = bytearray(raw)
        struct.pack_into("<H", partial, 89, 66)
        with self.assertRaisesRegex(project.InputError, "partially overlap"):
            animation.decode_active(partial)
        region = bytearray(164)
        struct.pack_into("<HH16H", region, 0, 164, 0, *([36, 100] + [65535] * 14))
        struct.pack_into("<32H", region, 36, *([64] + [65535] * 31))
        struct.pack_into("<32H", region, 100, *([65535] * 3 + [28] + [65535] * 28))
        incompatible = bytes(42) + b"SPRI" + struct.pack("<H", 2) + region
        with self.assertRaisesRegex(project.InputError, "alias incompatible"):
            animation.decode_active(incompatible)

    def test_atomic_write_repeat_failure_and_symlinks(self):
        doc = {"source": {"sha256": "a" * 64}, "value": 1}
        (project.REPO / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            target = animation.save_animations(doc, repo)
            initial = target.read_bytes()
            self.assertEqual(json.loads(initial), doc)
            self.assertEqual(animation.save_animations(doc, repo).read_bytes(), initial)
            with patch.object(project.os, "replace", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError):
                    animation.save_animations({**doc, "value": 2}, repo)
            self.assertEqual(target.read_bytes(), initial)
            self.assertEqual(list(target.parent.iterdir()), [target])
            victim = repo / "victim"
            victim.write_bytes(b"keep")
            target.unlink()
            target.symlink_to(victim)
            with self.assertRaises(project.InputError):
                animation.save_animations(doc, repo)
            self.assertEqual(victim.read_bytes(), b"keep")

    def test_fault_classification_and_safe_delivery_context(self):
        with patch.object(animation.sys, "argv", ["animation", "unused", "--klikback-src", "unused"]), \
                patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad")):
                self.assertEqual(animation.main(), 2)
            report.assert_not_called()
            with patch.object(project, "load_reader", side_effect=RuntimeError("private")):
                self.assertEqual(animation.main(), 1)
            report.assert_called_once_with("RuntimeError", version=animation.VERSION,
                                          title="Animation exporter crashed")
            report.reset_mock()
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""), \
                    patch.object(animation, "animation_document", return_value={}), \
                    patch.object(animation, "save_animations", side_effect=OSError("private")):
                self.assertEqual(animation.main(), 1)
            report.assert_called_once_with("OSError", version=animation.VERSION,
                                          title="Animation exporter crashed")


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_local_global_deleted_reference_only_and_repeated_banks(self):
        raw = project_bytes(duplicate_bank=True)
        doc = animation.animation_document(self.reader, raw)
        objects = doc["frames"][0]["object_lists"][0]["objects"]
        self.assertEqual([o["id"] for o in objects], [0, 1, 2])
        self.assertTrue(objects[1]["deleted"])
        self.assertTrue(objects[2]["global"])
        self.assertEqual(objects[2]["active_data"], [])
        self.assertEqual(doc["image_banks"][0]["slots"], [2, 5])
        self.assertEqual(len(doc["image_banks"]), 2)
        self.assertNotEqual(doc["image_banks"][0]["segment_id"], doc["image_banks"][1]["segment_id"])
        self.assertEqual(len(doc["global_object_lists"][0]["objects"][0]["active_data"]), 1)
        self.assertTrue(doc["coverage"]["image_handles"])
        self.assertFalse(doc["coverage"]["behaviour"])
        self.assertEqual(animation.animation_document(self.reader, raw), doc)

    def test_missing_handle_and_late_invalid_active_refuse_document(self):
        for data in [active_data((3,)), b"bad"]:
            with self.assertRaises(project.InputError):
                animation.animation_document(self.reader, project_bytes(data))

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_each_direction_and_handle_directly_from_source(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        doc = animation.animation_document(self.reader, raw)
        pairs = [(s.data, out["objects"], True) for s, out in zip(
            [s for s in game.segments if s.ident == 6], doc["global_object_lists"])]
        for level, frame in zip(game.levels(), doc["frames"]):
            pairs += [(b.data, out["objects"], False) for b, out in zip(
                [b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2], frame["object_lists"])]
        totals = [0, 0, 0, 0, 0]
        from klikback.core.tgf.icon_census import sprite_first_frame
        for data, objects, global_list in pairs:
            parsed = self.reader.object_definitions(data, globals_have_blocks=global_list)
            self.assertEqual(len(parsed), len(objects))
            for obj, out in zip(parsed, objects):
                if obj.object_type != 2:
                    continue
                if not obj.blocks:
                    totals[3] += 1
                original_blocks = [b for b in obj.blocks if b.ident == 0]
                self.assertEqual(len(original_blocks), len(out["active_data"]))
                for block, active in zip(original_blocks, out["active_data"]):
                    totals[0] += 1
                    source = block.data
                    self.assertEqual(bytes.fromhex(active["raw_hex"]), source)
                    base = 46 + int.from_bytes(source[46:48], "little")
                    first = None
                    for a in active["animations"]:
                        ptr = int.from_bytes(source[base + 4 + 2 * a["id"]:base + 6 + 2 * a["id"]], "little")
                        self.assertEqual(a["pointer_raw_u16"], ptr)
                        if ptr >= 32768:
                            self.assertIsNone(a["directions"])
                            continue
                        totals[1] += 1
                        at = base + ptr
                        self.assertEqual(a["offset"], at)
                        for d in a["directions"]:
                            dp = int.from_bytes(source[at + 2 * d["id"]:at + 2 * d["id"] + 2], "little")
                            self.assertEqual(d["pointer_raw_u16"], dp)
                            if dp >= 32768:
                                self.assertIsNone(d["image_ids"])
                                continue
                            totals[4] += 1
                            dt = at + dp
                            self.assertEqual(d["offset"], dt)
                            self.assertEqual(bytes.fromhex(d["header_hex"]), source[dt:dt + 8])
                            n = int.from_bytes(source[dt + 6:dt + 8], "little")
                            expected = [int.from_bytes(source[dt + 8 + 2 * j:dt + 10 + 2 * j], "little") for j in range(n)]
                            self.assertEqual(d["image_ids"], expected)
                            totals[2] += len(expected)
                            if first is None and expected:
                                first = expected[0]
                    self.assertEqual(first, sprite_first_frame(source))
        self.assertEqual(totals, [83, 131, 940, 815, 256])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(animation.animation_document(self.reader, raw), doc)


if __name__ == "__main__":
    unittest.main()
