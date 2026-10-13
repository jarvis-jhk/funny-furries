import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import export_project as bundle, frame_layout as layout, project_index as project
from test_frame_layout import placement_block, reconstruct
from test_event_references import synthetic_references


def obj(slot, name="own name", **changes):
    return {"id": slot, "name": name, "type": 2, "type_name": "active",
            "flags": 0x80, "global": True, "deleted": False, **changes}


def placements(words, pointers=None):
    records = b"".join(struct.pack("<H", w) + bytes(range(2, 32)) for w in words)
    if pointers is None:
        pointers = [32 * i for i in range(len(words))]
    raw = placement_block(pointers, records)
    return raw, layout.decode_placements(raw)


def synthetic_probes():
    raw, _ = synthetic_references()
    # Rebuild every frame with a placement block before its existing blocks;
    # the object-definition block identity must therefore be 1, not 0.
    reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))
    game = reader.read(raw)
    header = bytearray(raw[:game.level_addresses[0] - 6])
    body = b""
    placement, _ = placements([0, 7], [32, layout.UNUSED, 0, 32])
    for i, level in enumerate(game.levels()):
        start, _ = reader.level_blocks(level.data)
        frame = level.data[:start] + struct.pack("<HI", 3, len(placement)) + placement + level.data[start:]
        struct.pack_into("<I", header, 0x166 + 4 * i, len(header) + len(body) + 6)
        body += struct.pack("<HI", 0x8008 if i == 3 else 8, len(frame)) + frame
    return bytes(header) + body, placement


class ProbeTests(unittest.TestCase):
    def test_reversed_pointer_order_aliases_gaps_and_raw_fields_unchanged(self):
        raw, out = placements([3, 5], [32, layout.UNUSED, 0, 32])
        before = copy.deepcopy(out)
        lists = [(8, [obj(3, 'name\n"quote"'), obj(5, "other", type=32)])]
        old_lists = copy.deepcopy(lists)
        layout.annotate_object_slot_probes([out], lists)
        self.assertEqual([r["object_slot_probe"]["word_raw_u16"] for r in out["records"]], [3, 5])
        for rec in out["records"]:
            probe = rec.pop("object_slot_probe")
            self.assertEqual(probe["status"], "local_slot_probe")
            self.assertFalse(probe["runtime_resolution"])
            self.assertEqual(probe["candidates"][0]["block_id"], 8)
        self.assertEqual(out, before)
        self.assertEqual(lists, old_lists)
        self.assertEqual(reconstruct(out), raw)

    def test_missing_deleted_and_ambiguous_candidates_keep_all_definitions(self):
        for lists, status in [([], "missing_local_slot"),
            ([(4, [obj(3, deleted=True)])], "deleted_local_slot"),
            ([(4, [obj(3, deleted=True)]), (9, [obj(3, type=7, **{"global": False})])], "ambiguous_local_slot")]:
            with self.subTest(status=status):
                _, out = placements([3])
                layout.annotate_object_slot_probes([out], lists)
                probe = out["records"][0]["object_slot_probe"]
                self.assertEqual(probe["status"], status)
                self.assertEqual(probe["candidates"], [{"block_id": block, **o} for block, entries in lists for o in entries])
                self.assertEqual(probe["record_offset"], 0)
                self.assertEqual(probe["evidence"], "stored_word_local_slot_equality")

    def test_unsigned_boundaries_do_not_borrow_event_encodings_or_sentinels(self):
        words = [0, 0x3FFF, 0x4000, 0x8000, 0xFFFF]
        raw, out = placements(words)
        layout.annotate_object_slot_probes([out], [(6, [obj(w) for w in words])])
        probes = [r["object_slot_probe"] for r in out["records"]]
        self.assertEqual([p["word_raw_u16"] for p in probes], words)
        self.assertTrue(all(p["status"] == "local_slot_probe" for p in probes))
        self.assertEqual(reconstruct(out), raw)

    def test_empty_repeated_blocks_and_serialized_names_remain_lossless(self):
        raw, first = placements([0])
        _, second = placements([1])
        _, empty = placements([], [layout.UNUSED])
        blocks = [first, empty, second]
        layout.annotate_object_slot_probes(blocks, [(2, [obj(0, 'name\n"quote"')])])
        self.assertEqual(first["records"][0]["object_slot_probe"]["candidates"][0]["name"], 'name\n"quote"')
        self.assertIn('name\\n\\"quote\\"', json.dumps(blocks))
        self.assertEqual(second["records"][0]["object_slot_probe"]["status"], "missing_local_slot")
        self.assertEqual(empty["records"], [])
        self.assertEqual(reconstruct(first), raw)


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ProbeContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_same_frame_scope_actual_block_identity_and_repeated_list_ambiguity(self):
        raw, placement = synthetic_probes()
        out = layout.layout_document(self.reader, raw)
        self.assertEqual((out["schema_version"], out["exporter"]), (2, "frame-layout/2"))
        self.assertTrue(out["coverage"]["placement_object_slot_probes"])
        for key in ["placement_semantics", "arena_geometry", "spawns", "behaviour"]:
            self.assertFalse(out["coverage"][key])
        probes = []
        for frame in out["frames"]:
            block = frame["placements"][0]
            self.assertEqual(reconstruct(block), placement)
            self.assertEqual(block["block_id"], 0)
            probes.append(block["records"][0]["object_slot_probe"])
            self.assertEqual(block["records"][1]["object_slot_probe"]["status"], "missing_local_slot")
        self.assertEqual([p["status"] for p in probes], ["local_slot_probe", "local_slot_probe", "missing_local_slot", "ambiguous_local_slot"])
        self.assertEqual([[o["name"] for o in p["candidates"]] for p in probes], [["first"], ["second"], [], ["one", "two"]])
        self.assertEqual([o["block_id"] for o in probes[3]["candidates"]], [1, 2])
        self.assertEqual(layout.layout_document(self.reader, raw), out)

    def test_global_definition_is_not_a_frame_candidate(self):
        raw, _ = synthetic_probes()
        inventory = project.inventory(self.reader, raw)
        inventory["global_object_lists"] = [[obj(7, "global only")]]
        with patch.object(project, "inventory", return_value=inventory):
            out = layout.layout_document(self.reader, raw)
        self.assertTrue(all(f["placements"][0]["records"][1]["object_slot_probe"]["candidates"] == [] for f in out["frames"]))

    def test_bundle_repeats_and_late_invalid_placement_precedes_writes_and_reports(self):
        raw, _ = synthetic_probes()
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest["components"]["frame-layout.json"], {"exporter": "frame-layout/2", "schema_version": 2})
        (project.REPO / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch)), target)
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, files)
        bad = bytearray(raw)
        level = self.reader.read(raw).levels()[-1]
        _, blocks = self.reader.level_blocks(level.data)
        placement = next(b for b in blocks if b.ident == 3)
        struct.pack_into("<I", bad, level.offset + 6 + placement.offset + 6 + 2, 1)
        for module, save in [(layout, "save_layout"), (bundle, "save_bundle")]:
            with self.subTest(module=module.VERSION), patch.object(module.sys, "argv", ["export", "unused", "--klikback-src", os.environ["FF_KLIKBACK_SRC"]]), \
                    patch.object(Path, "read_bytes", return_value=bytes(bad)), \
                    patch.object(module, save) as write, patch.object(project, "report_fault") as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_words_and_local_slots_independently_walked(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        out = layout.layout_document(self.reader, raw)
        counts = []
        for frame, level in zip(out["frames"], self.reader.read(raw).levels()):
            _, blocks = self.reader.level_blocks(level.data)
            registry = {}
            for block_id, block in enumerate(blocks):
                if block.ident == 2:
                    for o in self.reader.object_definitions(block.data):
                        registry.setdefault(o.index, []).append({"block_id": block_id, "id": o.index,
                            "name": o.name, "type": o.object_type, "type_name": o.type_name,
                            "flags": o.flags, "global": o.is_global, "deleted": o.deleted})
            for placement in frame["placements"]:
                source = blocks[placement["block_id"]].data
                self.assertEqual(reconstruct(placement), source)
                for record in placement["records"]:
                    word = int.from_bytes(source[record["offset"]:record["offset"] + 2], "little")
                    probe = record["object_slot_probe"]
                    self.assertEqual(probe["word_raw_u16"], word)
                    self.assertEqual(probe["candidates"], registry.get(word, []))
                    self.assertEqual(probe["status"], "local_slot_probe")
                    self.assertFalse(probe["runtime_resolution"])
                    self.assertEqual(record["meaning"], "unknown")
                counts.append(len(placement["records"]))
        self.assertEqual(counts, [3, 75, 805, 845, 732, 872, 878, 609, 689, 741, 817, 902])
        self.assertEqual(sum(counts), 7968)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), hashlib.sha256(raw).digest())
        self.assertEqual(layout.layout_document(self.reader, raw), out)


if __name__ == "__main__":
    unittest.main()
