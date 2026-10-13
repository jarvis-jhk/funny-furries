import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import project_index as exporter


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (exporter.REPO / "build").mkdir(exist_ok=True)

    def test_atomic_deterministic_output_and_failed_replace(self):
        document = {"source": {"sha256": "a" * 64}, "value": "synthetic"}
        with tempfile.TemporaryDirectory(dir=exporter.REPO / "build") as scratch:
            repo = Path(scratch)
            target = exporter.save_index(document, repo)
            initial = target.read_bytes()
            self.assertEqual(json.loads(initial), document)
            self.assertEqual(exporter.save_index(document, repo).read_bytes(), initial)
            with patch.object(exporter.os, "replace", side_effect=OSError("test fault")):
                with self.assertRaises(OSError):
                    exporter.save_index({**document, "value": "changed"}, repo)
            self.assertEqual(target.read_bytes(), initial)
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_symlink_output_refused(self):
        document = {"source": {"sha256": "a" * 64}}
        with tempfile.TemporaryDirectory(dir=exporter.REPO / "build") as scratch:
            repo = Path(scratch)
            outside = repo / "outside"
            outside.mkdir()
            (repo / "export").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(exporter.InputError):
                exporter.save_index(document, repo)
            self.assertEqual(list(outside.iterdir()), [])
            (repo / "export").unlink()
            directory = repo / "export" / ("a" * 64)
            directory.mkdir(parents=True)
            victim = outside / "victim"
            victim.write_text("keep")
            (directory / "project-index.json").symlink_to(victim)
            with self.assertRaises(exporter.InputError):
                exporter.save_index(document, repo)
            self.assertEqual(victim.read_text(), "keep")
            (directory / "project-index.json").unlink()
            directory.rmdir()
            directory.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(exporter.InputError):
                exporter.save_index(document, repo)

    def test_fault_report_is_detached_and_has_only_safe_context(self):
        with patch.dict(os.environ, {"FF_FAULT_REPORT_URL": "https://example.invalid/report"}):
            with patch.object(exporter.subprocess, "Popen") as spawn:
                exporter.report_fault("RuntimeError")
            args, kwargs = spawn.call_args
            report = json.loads(args[0][-1])
            self.assertEqual(report["lane"], "furries")
            self.assertEqual(report["detail"], "RuntimeError")
            self.assertEqual(set(report), {"lane", "kind", "title", "detail", "source"})
            self.assertTrue(kwargs["start_new_session"])
            self.assertEqual(kwargs["stdout"], exporter.subprocess.DEVNULL)

    def test_expected_input_error_is_not_reported(self):
        with patch.object(exporter.sys, "argv", ["exporter", "missing", "--klikback-src", "missing"]):
            with patch.object(exporter, "report_fault") as report:
                self.assertEqual(exporter.main(), 2)
                report.assert_not_called()

    def test_unexpected_fault_is_reported_and_does_not_save(self):
        with patch.object(exporter.sys, "argv", ["exporter", "missing", "--klikback-src", "missing"]):
            with patch.object(exporter, "load_reader", side_effect=RuntimeError("private path")):
                with patch.object(exporter, "report_fault") as report, patch.object(exporter, "save_index") as save:
                    self.assertEqual(exporter.main(), 1)
                    report.assert_called_once_with("RuntimeError")
                    save.assert_not_called()

    def test_output_write_fault_is_reported(self):
        with patch.object(exporter.sys, "argv", ["exporter", "unused", "--klikback-src", "unused"]):
            with patch.object(exporter, "load_reader"), patch.object(Path, "read_bytes", return_value=b""):
                with patch.object(exporter, "inventory", return_value={}):
                    with patch.object(exporter, "save_index", side_effect=OSError("private directory")):
                        with patch.object(exporter, "report_fault") as report:
                            self.assertEqual(exporter.main(), 1)
                            report.assert_called_once_with("OSError")


def synthetic_project():
    def obj(name, kind, flags=0, chain=b""):
        head = bytearray(0x44)
        head[:len(name)] = name
        head[0x26], head[0x2A] = flags, kind
        return bytes(head) + chain

    def segment(kind, data):
        return struct.pack("<HI", kind, len(data)) + data

    objects = struct.pack("<HH", 3, 0)
    objects += obj(b"Synthetic", 2, chain=segment(0x8000, b"own-test-data"))
    objects += obj(b"Removed", 0xFF)
    objects += obj(b"Shared", 2, flags=0x80)
    level = bytes(0xB8) + segment(0x8002, objects)
    header = bytearray(0x16A)
    header[:4] = b"GAME"
    struct.pack_into("<H", header, 4, 0x0207)
    struct.pack_into("<H", header, 0x15C, 1)
    struct.pack_into("<I", header, 0x166, len(header) + 6)
    bank = struct.pack("<I", 3) + bytes(16) + struct.pack("<II", 28, 4) + b"test"
    return bytes(header) + segment(8, level) + segment(0x800A, bank)


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = exporter.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_synthetic_project_preserves_slots_offsets_and_coverage(self):
        raw = synthetic_project()
        document = exporter.inventory(self.reader, raw)
        self.assertEqual(document["source"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(document["source"]["bytes"], len(raw))
        self.assertEqual(document["coverage"], {"inventory": True, "event_semantics": False,
                                               "asset_files": False, "arena_geometry": False})
        objects = document["frames"][0]["object_lists"][0]
        self.assertEqual([o["id"] for o in objects], [0, 1, 2])
        self.assertTrue(objects[1]["deleted"])
        self.assertTrue(objects[2]["global"])
        self.assertEqual(objects[0]["name"], "Synthetic")
        self.assertEqual(objects[0]["offset"], 4)
        self.assertEqual(objects[0]["blocks"][0]["offset"], 4 + 0x44)
        self.assertEqual(document["banks"][0]["entries"], [{"id": 2, "offset": 28, "bytes": 4}])
        self.assertEqual(exporter.inventory(self.reader, raw), document)

    def test_malformed_or_wrong_family_projects_fail(self):
        raw = synthetic_project()
        bad_address = bytearray(raw)
        struct.pack_into("<I", bad_address, 0x166, 1)
        bad_count = bytearray(raw)
        struct.pack_into("<H", bad_count, 0x15C, 0)
        bad_bank = bytearray(raw)
        struct.pack_into("<I", bad_bank, len(raw) - 8, 10000)
        for invalid in [b"", raw[:-1], b"PAME" + raw[4:], b"GAPP" + raw[4:],
                        bytes(bad_address), bytes(bad_count), bytes(bad_bank)]:
            with self.subTest(size=len(invalid)):
                with self.assertRaises(ValueError):
                    exporter.inventory(self.reader, invalid)

    def test_object_list_truncation_and_trailing_data_fail(self):
        for data in [b"", bytes(3), struct.pack("<HH", 1, 0), bytes(4) + b"extra"]:
            with self.assertRaises(ValueError):
                exporter.object_index(self.reader, data)

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_inventory(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        document = exporter.inventory(self.reader, raw)
        self.assertEqual(len(document["frames"]), 13)
        self.assertEqual(len(document["global_object_lists"][0]), 133)
        self.assertEqual([len(f["object_lists"][0]) if f["object_lists"] else 0
                          for f in document["frames"]], [0, 3, 111] + [137] * 10)
        self.assertEqual({b["kind"]: len(b["entries"]) for b in document["banks"]},
                         {"image": 614, "music": 2, "sound": 17})
        self.assertEqual(path.read_bytes(), raw)
        with tempfile.TemporaryDirectory(dir=exporter.REPO / "build") as scratch:
            target = exporter.save_index(document, Path(scratch))
            first = target.read_bytes()
            exporter.save_index(exporter.inventory(self.reader, path.read_bytes()), Path(scratch))
            self.assertEqual(target.read_bytes(), first)
            self.assertEqual(json.loads(first), document)


if __name__ == "__main__":
    (exporter.REPO / "build").mkdir(exist_ok=True)
    unittest.main()
