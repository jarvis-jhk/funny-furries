import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import backdrop_dump as backdrop
from tools import project_index as project
from test_image_dump import record as image_record


def header(kind=0, fill=0, image=65535, flags=0x80):
    head = bytearray(68)
    # Nonzero high COLORREF bytes must remain raw without becoming alpha.
    struct.pack_into("<II", head, 24, 0x7F563412, 0xFEDCBA98)
    head[32], head[38], head[42] = fill, flags, kind
    struct.pack_into("<H", head, 54, image)
    return bytes(head)


def project_bytes(heads=None, bank_slots=(2, 5), repeated=False, image_records=None):
    def block(kind, data):
        return struct.pack("<HI", kind, len(data)) + data
    def definitions(heads, global_list=False):
        result = struct.pack("<HH", len(heads), 0)
        for head in heads:
            result += head
            if head[42] != 255 and (global_list or not head[38] & 128):
                result += block(0x8000, b"opaque")
        return result
    heads = heads if heads is not None else [header(1, image=5), header(fill=1, image=2),
        header(fill=0x12, image=40000), header(fill=0, image=65535),
        header(255), header(2), header(1, image=2, flags=0)]
    globals_ = block(6, definitions([header(1, image=2), header(fill=2)], True))
    first = bytes(184) + block(0x8000, b"palette")
    second = bytes(184) + block(2, definitions([])) + block(0x8002, definitions(heads))
    game = bytearray(366)
    game[:4] = b"GAME"
    struct.pack_into("<H", game, 4, 0x0207)
    struct.pack_into("<H", game, 348, 2)
    struct.pack_into("<II", game, 358, len(game) + len(globals_) + 6,
                     len(game) + len(globals_) + len(first) + 12)
    bank = bytearray(4 + 6 * 8)
    struct.pack_into("<I", bank, 0, 6)
    for slot in bank_slots:
        data = image_records[slot] if image_records is not None else image_record()
        struct.pack_into("<II", bank, 4 + slot * 8, len(bank), len(data))
        bank += data
    banks = block(10 if repeated else 0x800A, bank)
    if repeated:
        banks += block(10, struct.pack("<I", 0)) + block(0x800A, bank)
    return bytes(game) + globals_ + block(8, first) + block(8, second) + banks


class BackdropTests(unittest.TestCase):
    def test_known_picture_solid_mosaic_and_both_gradient_axes(self):
        for kind, fill, expected, image, axis in [
            (1, 0xFF, "image", 5, None), (0, 0, "solid", None, None),
            (0, 1, "mosaic", 5, None), (0, 2, "gradient", None, "vertical"),
            (0, 0x12, "gradient", None, "horizontal")]:
            with self.subTest(kind=kind, fill=fill):
                raw = header(kind, fill, 5)
                decoded = backdrop.decode_header(raw)
                art = decoded["artwork"]
                self.assertEqual((art["kind"], art["image_id"]), (expected, image))
                self.assertEqual(art.get("gradient_axis"), axis)
                self.assertEqual(decoded["image_word_raw_u16"], 5)
                self.assertEqual(decoded["header_hex"], raw.hex())
                self.assertEqual(decoded["header_sha256"], hashlib.sha256(raw).hexdigest())
                if kind == 0:
                    self.assertEqual(art["colors"], [
                        {"raw_u32": 0x7F563412, "rgb": [18, 52, 86]},
                        {"raw_u32": 0xFEDCBA98, "rgb": [152, 186, 220]}])

    def test_bad_header_type_truncation_and_unknown_fill(self):
        bad = [b"", header()[:-1], header() + b"x", header(2), header(255)]
        bad += [header(fill=value) for value in (3, 15, 0x13, 0x20, 0x82, 0xFF)]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(project.InputError):
                    backdrop.decode_header(raw)

    def test_atomic_repeat_failed_write_and_symlink_refusal(self):
        doc = {"source": {"sha256": "a" * 64}, "value": 1}
        (project.REPO / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            target = backdrop.save_backdrops(doc, repo)
            initial = target.read_bytes()
            self.assertEqual(json.loads(initial), doc)
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), initial)
            with patch.object(project.os, "replace", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError):
                    backdrop.save_backdrops({**doc, "value": 2}, repo)
            self.assertEqual(target.read_bytes(), initial)
            self.assertEqual(list(target.parent.iterdir()), [target])
            victim = repo / "victim"
            victim.write_bytes(b"keep")
            target.unlink()
            target.symlink_to(victim)
            with self.assertRaises(project.InputError):
                backdrop.save_backdrops(doc, repo)
            self.assertEqual(victim.read_bytes(), b"keep")

    def test_cli_input_fault_write_fault_and_safe_delivery_context(self):
        with patch.object(backdrop.sys, "argv", ["backdrop", "unused", "--klikback-src", "unused"]), \
                patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad")):
                self.assertEqual(backdrop.main(), 2)
            report.assert_not_called()
            with patch.object(project, "load_reader", side_effect=RuntimeError("private")):
                self.assertEqual(backdrop.main(), 1)
            report.assert_called_once_with("RuntimeError", version=backdrop.VERSION,
                                          title="Backdrop exporter crashed")
            report.reset_mock()
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""), \
                    patch.object(backdrop, "backdrop_document", return_value={}), \
                    patch.object(backdrop, "save_backdrops", side_effect=OSError("private")):
                self.assertEqual(backdrop.main(), 1)
            report.assert_called_once_with("OSError", version=backdrop.VERSION,
                                          title="Backdrop exporter crashed")


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_all_slots_global_headers_local_data_missing_empty_lists_repeated_banks(self):
        raw = project_bytes(repeated=True)
        doc = backdrop.backdrop_document(self.reader, raw)
        self.assertEqual(doc["frames"][0]["object_lists"], [])
        lists = doc["frames"][1]["object_lists"]
        self.assertEqual([v["block_id"] for v in lists], [0, 1])
        self.assertEqual(lists[0]["objects"], [])
        objects = lists[1]["objects"]
        self.assertEqual([o["id"] for o in objects], list(range(7)))
        self.assertEqual([o["global"] for o in objects], [True] * 6 + [False])
        self.assertEqual([o["deleted"] for o in objects], [False] * 4 + [True, False, False])
        self.assertIsNone(objects[4]["backdrop"])
        self.assertIsNone(objects[5]["backdrop"])
        self.assertEqual([bank["slots"] for bank in doc["image_banks"]], [[2, 5], [], [2, 5]])
        candidates = [doc["image_banks"][i]["segment_id"] for i in (0, 2)]
        self.assertEqual(objects[0]["backdrop"]["artwork"]["image_bank_candidates"], candidates)
        self.assertEqual(objects[1]["backdrop"]["artwork"]["image_bank_candidates"], candidates)
        self.assertEqual(objects[2]["backdrop"]["artwork"]["image_bank_candidates"], [])
        self.assertEqual(objects[2]["backdrop"]["image_word_raw_u16"], 40000)
        self.assertEqual(doc["global_object_lists"][0]["objects"][0]["backdrop"]["artwork"]["image_id"], 2)
        self.assertTrue(doc["coverage"]["backdrop_header_artwork"])
        self.assertFalse(doc["coverage"]["global_reference_resolution"])
        self.assertFalse(doc["coverage"]["arena_geometry"])
        self.assertEqual(backdrop.backdrop_document(self.reader, raw), doc)

    def test_missing_used_image_and_late_invalid_fill_validate_before_write(self):
        for heads in [[header(1, image=3)], [header(fill=1)],
                      [header(1, image=2), header(fill=3)]]:
            with self.subTest(heads=heads), patch.object(backdrop, "save_backdrops") as save:
                with tempfile.TemporaryDirectory() as scratch:
                    path = Path(scratch) / "synthetic.cca"
                    path.write_bytes(project_bytes(heads))
                    with patch.object(backdrop.sys, "argv", ["backdrop", str(path), "--klikback-src",
                                                            os.environ["FF_KLIKBACK_SRC"]]), \
                            patch.object(project, "report_fault") as report:
                        self.assertEqual(backdrop.main(), 2)
                    save.assert_not_called()
                    report.assert_not_called()

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_headers_handles_colors_and_independent_icon_oracle(self):
        from klikback.core.tgf.icon_census import source_handle
        from klikback.core.tgf.icon_generate import quick_backdrop_icon
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        doc = backdrop.backdrop_document(self.reader, raw)
        pairs = [(s.data, out["objects"], True) for s, out in zip(
            [s for s in game.segments if s.ident == 6], doc["global_object_lists"])]
        self.assertEqual(len(doc["frames"]), 13)
        for level, frame in zip(game.levels(), doc["frames"]):
            pairs += [(b.data, out["objects"], False) for b, out in zip(
                [b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2], frame["object_lists"])]
        counts = {"image": 0, "mosaic": 0, "gradient": 0}
        refs = 0
        for data, objects, global_list in pairs:
            parsed = self.reader.object_definitions(data, globals_have_blocks=global_list)
            self.assertEqual(len(parsed), len(objects))
            for obj, out in zip(parsed, objects):
                if obj.object_type not in (0, 1):
                    self.assertIsNone(out["backdrop"])
                    continue
                head = data[obj.base:obj.base + 68]
                decoded = out["backdrop"]
                self.assertEqual(out["object_list_offset"], obj.base)
                self.assertEqual(bytes.fromhex(decoded["header_hex"]), head)
                self.assertEqual(decoded["header_sha256"], hashlib.sha256(head).hexdigest())
                art = decoded["artwork"]
                counts[art["kind"]] += 1
                expected = source_handle(obj, head)
                self.assertEqual(decoded["image_word_raw_u16"], expected)
                if art["image_id"] is not None:
                    refs += 1
                    self.assertEqual(art["image_id"], expected)
                    matching = [i for i, s in enumerate(game.segments) if s.ident == 10
                                and expected in [slot for slot, _, _ in self.reader.walk_bank(s.data)]]
                    self.assertEqual(art["image_bank_candidates"], matching)
                if obj.object_type == 0:
                    for color, at in zip(art["colors"], (24, 28)):
                        self.assertEqual(color["raw_u32"], int.from_bytes(head[at:at + 4], "little"))
                        self.assertEqual(color["rgb"], list(head[at:at + 3]))
                    if art["kind"] == "gradient":
                        sampled = []
                        quick_backdrop_icon(head, lambda rgb: sampled.append(rgb) or 0)
                        self.assertEqual(list(sampled[0]), art["colors"][0]["rgb"])
                        self.assertEqual(list(sampled[-1]), art["colors"][1]["rgb"])
                        self.assertEqual(art["gradient_axis"], "vertical")
        self.assertEqual(counts, {"image": 352, "mosaic": 30, "gradient": 28})
        self.assertEqual(refs, 382)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(backdrop.backdrop_document(self.reader, raw), doc)


if __name__ == "__main__":
    unittest.main()
