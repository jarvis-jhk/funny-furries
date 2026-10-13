import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import frame_layout as layout
from tools import project_index as project


def placement_block(pointers, records):
    return struct.pack("<H", len(pointers)) + struct.pack(f"<{len(pointers)}I", *pointers) + records


def reconstruct(document):
    pointers = [slot["pointer_raw_u32"] for slot in document["slots"]]
    return placement_block(pointers, b"".join(bytes.fromhex(r["raw_hex"]) for r in document["records"]))


def synthetic_layout():
    def block(kind, data):
        return struct.pack("<HI", kind, len(data)) + data
    header = bytearray(0x16E)
    header[:4] = b"GAME"
    struct.pack_into("<H", header, 4, 0x0207)
    struct.pack_into("<H", header, 0x15C, 2)
    a, b = bytes(range(32)), bytes(range(255, 223, -1))
    first = bytes(0xB8) + block(0x8000, b"palette")
    second = bytes(range(0x78)) + block(0, b"palette")
    second += block(3, placement_block([32, layout.UNUSED, 0, 32], a + b))
    second += block(0x8003, placement_block([], b""))
    struct.pack_into("<II", header, 0x166, len(header) + 6, len(header) + 6 + len(first) + 6)
    return bytes(header) + block(8, first) + block(0x8008, second)


class PlacementTests(unittest.TestCase):
    def test_gaps_reversed_order_aliases_and_unknown_records(self):
        a, b = bytes(range(32)), bytes(range(255, 223, -1))
        raw = placement_block([32, layout.UNUSED, 0, 32], a + b)
        document = layout.decode_placements(raw)
        self.assertEqual([s["id"] for s in document["slots"]], [0, 1, 2, 3])
        self.assertEqual([s["record_id"] for s in document["slots"]], [1, None, 0, 1])
        self.assertEqual([r["offset"] for r in document["records"]], [18, 50])
        self.assertEqual([bytes.fromhex(r["raw_hex"]) for r in document["records"]], [a, b])
        self.assertTrue(all(r["meaning"] == "unknown" for r in document["records"]))
        self.assertEqual(document["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(reconstruct(document), raw)

    def test_empty_table_and_all_unused_slots(self):
        for pointers in [[], [layout.UNUSED] * 3]:
            raw = placement_block(pointers, b"")
            document = layout.decode_placements(raw)
            self.assertEqual(len(document["slots"]), len(pointers))
            self.assertEqual(document["records"], [])
            self.assertEqual(reconstruct(document), raw)

    def test_bad_table_pointers_truncation_and_unreferenced_data(self):
        invalid = [b"", b"\0", struct.pack("<H", 65535),
                   placement_block([0], bytes(31)), placement_block([0], bytes(33)),
                   placement_block([1], bytes(32)), placement_block([32], bytes(32)),
                   placement_block([0xFFFFFFFE], bytes(32)),
                   placement_block([layout.UNUSED], bytes(32)),
                   placement_block([0], bytes(64)), placement_block([], bytes(32))]
        for raw in invalid:
            with self.subTest(size=len(raw), head=raw[:8]):
                with self.assertRaises(project.InputError):
                    layout.decode_placements(raw)

    def test_atomic_deterministic_write_failure_and_symlinks(self):
        document = {"source": {"sha256": "a" * 64}, "frames": []}
        (project.REPO / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            target = layout.save_layout(document, repo)
            initial = target.read_bytes()
            self.assertEqual(json.loads(initial), document)
            self.assertEqual(layout.save_layout(document, repo).read_bytes(), initial)
            with patch.object(project.os, "replace", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError):
                    layout.save_layout({**document, "frames": [1]}, repo)
            self.assertEqual(target.read_bytes(), initial)
            self.assertEqual(list(target.parent.iterdir()), [target])
            victim = repo / "victim"
            victim.write_bytes(b"keep")
            target.unlink()
            target.symlink_to(victim)
            with self.assertRaises(project.InputError):
                layout.save_layout(document, repo)
            self.assertEqual(victim.read_bytes(), b"keep")

    def test_cli_fault_classification(self):
        argv = ["layout", "unused", "--klikback-src", "unused"]
        with patch.object(layout.sys, "argv", argv), patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad input")):
                self.assertEqual(layout.main(), 2)
            report.assert_not_called()
            with patch.object(project, "load_reader", side_effect=RuntimeError("private")):
                self.assertEqual(layout.main(), 1)
            report.assert_called_once_with("RuntimeError", version=layout.VERSION,
                                          title="Frame layout exporter crashed")
            report.reset_mock()
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""), \
                    patch.object(layout, "layout_document", return_value={}), \
                    patch.object(layout, "save_layout", side_effect=OSError("private")):
                self.assertEqual(layout.main(), 1)
            report.assert_called_once_with("OSError", version=layout.VERSION,
                                          title="Frame layout exporter crashed")


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_both_header_shapes_absent_empty_and_repeated_placement_blocks(self):
        raw = synthetic_layout()
        document = layout.layout_document(self.reader, raw)
        self.assertEqual([f["header_bytes"] for f in document["frames"]], [0xB8, 0x78])
        self.assertEqual(document["frames"][0]["placements"], [])
        second = document["frames"][1]
        self.assertEqual(second["header_hex"], bytes(range(0x78)).hex())
        self.assertEqual([b["block_id"] for b in second["placements"]], [1, 2])
        self.assertEqual([len(b["slots"]) for b in second["placements"]], [4, 0])
        self.assertTrue(document["coverage"]["placement_storage"])
        self.assertFalse(document["coverage"]["arena_geometry"])
        self.assertEqual(layout.layout_document(self.reader, raw), document)

    def test_late_malformed_block_refuses_whole_document(self):
        raw = synthetic_layout()
        # The final empty placement block has a complete count but no slot table.
        bad = raw[:-2] + struct.pack("<H", 1)
        with self.assertRaises(project.InputError):
            layout.layout_document(self.reader, bad)

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_lossless_headers_and_placement_blocks(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        document = layout.layout_document(self.reader, raw)
        self.assertEqual(len(document["frames"]), 13)
        counts = []
        for frame, level in zip(document["frames"], self.reader.read(raw).levels()):
            start, blocks = self.reader.level_blocks(level.data)
            self.assertEqual(bytes.fromhex(frame["header_hex"]), level.data[:start])
            expected = [(i, b) for i, b in enumerate(blocks) if b.ident == 3]
            self.assertEqual(len(frame["placements"]), len(expected))
            for (block_id, block), out in zip(expected, frame["placements"]):
                self.assertEqual(out["block_id"], block_id)
                self.assertEqual(out["frame_offset"], block.offset)
                self.assertEqual(reconstruct(out), block.data)
                count = int.from_bytes(block.data[:2], "little")
                base = 2 + 4 * count
                for slot in out["slots"]:
                    pointer = int.from_bytes(block.data[2 + 4 * slot["id"]:6 + 4 * slot["id"]], "little")
                    self.assertEqual(slot["pointer_raw_u32"], pointer)
                    if pointer != layout.UNUSED:
                        record = out["records"][slot["record_id"]]
                        self.assertEqual(bytes.fromhex(record["raw_hex"]), block.data[base + pointer:base + pointer + 32])
                counts.append((len(out["slots"]), len(out["records"])))
        self.assertEqual(counts, list(zip([3,411,949,987,952,999,1005,948,952,948,959,1028],
                                         [3,75,805,845,732,872,878,609,689,741,817,902])))
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(layout.layout_document(self.reader, raw), document)


if __name__ == "__main__":
    unittest.main()
