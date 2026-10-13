import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events
from tools import project_index as project
from test_project_index import synthetic_project


def record(role, kind, opcode, reference, parameters):
    header = bytearray(14 if role == "condition" else 12)
    struct.pack_into("<bbh", header, 2, kind, opcode, reference)
    header[10] = len(parameters)
    body = b"".join(struct.pack("<HH", 4 + len(payload), code) + payload
                    for code, payload in parameters)
    struct.pack_into("<H", header, 0, len(header) + len(body))
    return bytes(header) + body


def row(conditions, actions, positive=False):
    header = bytearray(14)
    header[2:4] = bytes([len(conditions), len(actions)])
    body = b"".join(conditions + actions)
    struct.pack_into("<h", header, 0, (1 if positive else -1) * (14 + len(body)))
    return bytes(header) + body


def sample_program():
    condition = record("condition", 2, -17, -32768, [(999, b"own-test-data"), (22, b"\0\xff")])
    action = record("action", -3, 7, 4, [])
    return row([condition], [action]) + row([], [action], positive=True) + bytes(2)


def event_block(program):
    return b"Fra\0" + struct.pack("<HI", 0x0217, len(program)) + program + b"\x02\0ABCD"


def reconstruct_program(document):
    out = b""
    for event_row in document["rows"]:
        out += bytes.fromhex(event_row["header_hex"])
        for rec in event_row["records"]:
            out += bytes.fromhex(rec["header_hex"])
            for parameter in rec["parameters"]:
                out += struct.pack("<HH", parameter["bytes"], parameter["type"])
                out += bytes.fromhex(parameter["payload_hex"])
    return out + bytes(2)


class StructureTests(unittest.TestCase):
    def test_order_parameters_unknowns_and_lossless_bytes(self):
        raw = sample_program()
        document = events.decode_program(event_block(raw))
        self.assertEqual(reconstruct_program(document), raw)
        first, second = document["rows"]
        self.assertEqual([r["role"] for r in first["records"]], ["condition", "action"])
        condition = first["records"][0]
        self.assertEqual((condition["object_type"], condition["opcode"], condition["object_reference"]),
                         (2, -17, -32768))
        self.assertEqual(condition["meaning"], "unknown")
        self.assertEqual([p["type"] for p in condition["parameters"]], [999, 22])
        self.assertEqual(condition["parameters"][0]["offset"], 28)
        self.assertEqual(condition["parameters"][0]["payload_hex"], b"own-test-data".hex())
        self.assertGreater(second["signed_size"], 0)
        self.assertEqual(second["offset"], first["bytes"])
        self.assertEqual(document["auxiliary"][0]["raw_hex"], b"AB".hex())
        self.assertEqual(document["auxiliary"][1]["raw_hex"], b"CD".hex())
        text = events.readable({"source": {"sha256": "a" * 64}, "frames": [
            {"id": 0, "programs": [{"block_id": 1, "frame_offset": 200, **document}]}],
            "global_events": []})
        self.assertLess(text.index("CONDITION 0"), text.index("ACTION 1"))
        self.assertIn("type=999 meaning=UNKNOWN", text)
        self.assertIn("reference=-32768 meaning=UNKNOWN", text)

    def test_empty_program_and_missing_terminator(self):
        self.assertEqual(events.decode_rows(bytes(2)), [])
        for raw in [b"", b"\0", sample_program()[:-2], bytes(2) + b"extra"]:
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(project.InputError):
                    events.decode_rows(raw)

    def test_bad_lengths_counts_and_trailing_bytes_fail(self):
        raw = sample_program()
        mutations = [(0, "<h", -13), (0, "<h", -32768), (2, "<B", 0),
                     (3, "<B", 10), (14, "<H", 13), (14, "<H", 65535),
                     (24, "<B", 0), (24, "<B", 3), (28, "<H", 3),
                     (28, "<H", 65535)]
        for offset, form, value in mutations:
            bad = bytearray(raw)
            struct.pack_into(form, bad, offset, value)
            with self.subTest(offset=offset, value=value):
                with self.assertRaises(project.InputError):
                    events.decode_rows(bytes(bad))
        action = bytearray(record("action", 2, 0, 1, []))
        action[10] = 1
        with self.assertRaises(project.InputError):
            events.decode_rows(row([], [bytes(action)]) + bytes(2))

    def test_event_header_and_auxiliary_truncation_fail(self):
        raw = event_block(sample_program())
        wrong_version = bytearray(raw)
        struct.pack_into("<H", wrong_version, 4, 0x999)
        bad_second = bytearray(raw)
        struct.pack_into("<H", bad_second, 10 + len(sample_program()), 100)
        for bad in [raw[6:], raw[:5], bytes(wrong_version), raw[:10],
                    raw[:-6], raw[:-5], bytes(bad_second)]:
            with self.assertRaises(project.InputError):
                events.decode_program(bad)

    def test_input_and_output_fault_classification(self):
        argv = ["event_dump", "unused", "--klikback-src", "unused"]
        with patch.object(events.sys, "argv", argv), patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad input")), \
                    patch.object(project, "save_export") as save:
                self.assertEqual(events.main(), 2)
                report.assert_not_called()
                save.assert_not_called()
            document = {"source": {"sha256": "a" * 64}}
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""):
                with patch.object(events, "event_document", return_value=document):
                    with patch.object(project, "save_export", side_effect=OSError("private path")):
                        self.assertEqual(events.main(), 1)
                        report.assert_called_once_with("OSError", version=events.VERSION,
                                                       title="Event exporter crashed")

    def test_atomic_text_json_and_symlink_protection(self):
        document = {"source": {"sha256": "a" * 64}}
        (project.REPO / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            for name in ["events.json", "events.txt"]:
                target = project.save_export(document, "previous\n", name, repo)
                with patch.object(project.os, "replace", side_effect=OSError):
                    with self.assertRaises(OSError):
                        project.save_export(document, "new\n", name, repo)
                self.assertEqual(target.read_text(), "previous\n")
                victim = repo / "victim"
                victim.write_text("keep")
                target.unlink()
                target.symlink_to(victim)
                with self.assertRaises(project.InputError):
                    project.save_export(document, "new\n", name, repo)
                self.assertEqual(victim.read_text(), "keep")
                target.unlink()


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (project.REPO / "build").mkdir(exist_ok=True)
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_synthetic_container_with_global_events_and_absent_frame_events(self):
        raw = synthetic_project()
        empty = events.event_document(self.reader, raw)
        self.assertEqual(empty["frames"], [{"id": 0, "programs": []}])
        game = self.reader.read(raw)
        level = bytearray(game.levels()[0].data)
        struct.pack_into("<H", level, 0xB8, 2)
        block = event_block(sample_program())
        level += struct.pack("<HI", 0x8004, len(block)) + block
        raw = game.raw[:0x16A] + struct.pack("<HI", 8, len(level)) + level
        raw += struct.pack("<HI", 0x8003, 7) + b"unknown"
        document = events.event_document(self.reader, raw)
        self.assertEqual(document["global_events"][0]["raw_hex"], b"unknown".hex())
        self.assertFalse(document["coverage"]["global_event_structure"])
        self.assertFalse(document["coverage"]["opcode_semantics"])
        self.assertEqual(reconstruct_program(document["frames"][0]["programs"][0]), sample_program())

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_all_rows_records_parameters_reconstruct_exactly(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        document = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        counts = [0, 0, 0]
        rows_by_frame = []
        for frame, level in zip(document["frames"], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            rows_by_frame.append(sum(len(p["rows"]) for p in frame["programs"]))
            for program in frame["programs"]:
                data = blocks[program["block_id"]].data
                rebuilt = reconstruct_program(program)
                self.assertEqual(rebuilt, data[10:10 + program["program_bytes"]])
                self.assertEqual([(r["offset"], r["bytes"]) for r in program["rows"]],
                                 self.reader.event_groups(rebuilt))
                for event_row in program["rows"]:
                    for rec in event_row["records"]:
                        counts[rec["role"] == "action"] += 1
                        counts[2] += len(rec["parameters"])
                        self.assertEqual(rec["meaning"], "unknown")
                second = bytes.fromhex(program["auxiliary"][0]["raw_hex"])
                third = bytes.fromhex(program["auxiliary"][1]["raw_hex"])
                self.assertEqual(bytes.fromhex(program["header_hex"]) + struct.pack("<I", len(rebuilt))
                                 + rebuilt + struct.pack("<H", len(second)) + second + third, data)
        self.assertEqual(rows_by_frame, [0, 4, 52] + [113] * 10)
        self.assertEqual(counts, [2490, 5083, 6685])
        self.assertEqual(bytes.fromhex(document["global_events"][0]["raw_hex"]), game.segment(3).data)
        self.assertEqual(document["source"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(events.event_document(self.reader, raw), document)
        self.assertEqual(path.read_bytes(), raw)
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            for name, payload in [("events.json", json.dumps(document, sort_keys=True)),
                                  ("events.txt", events.readable(document))]:
                target = project.save_export(document, payload, name, Path(scratch))
                before = target.read_bytes()
                self.assertEqual(project.save_export(document, payload, name, Path(scratch)).read_bytes(), before)
