import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from tools import audio_dump as audio
from tools import project_index as project
from test_project_index import synthetic_project


def audio_record(kind, body):
    header = bytearray(32)
    header[10:14] = b"test"
    struct.pack_into("<I", header, 6, len(body))
    struct.pack_into("<H", header, 30, kind)
    return bytes(header) + body


def pcm(samples=b"\0\x80\xff", channels=1, bits=8, rate=11025):
    align = channels * bits // 8
    return audio_record(1, struct.pack("<HHIIHH", 1, channels, rate,
                                      rate * align, align, bits) + samples)


def midi():
    track = b"\0\x90\x3c\x40\x60\x80\x3c\0\0\xff\x2f\0"
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, 96) + b"MTrk" + struct.pack(">I", len(track)) + track


def bank(entries):
    count = max(entries, default=-1) + 1
    cursor = 4 + count * 8
    table, body = bytearray(struct.pack("<I", count)), b""
    for slot in range(count):
        data = entries.get(slot)
        table += struct.pack("<II", cursor if data is not None else 0, len(data or b""))
        if data is not None:
            body += data
            cursor += len(data)
    return bytes(table) + body


def with_banks(reader, segments):
    game = reader.read(synthetic_project())
    parts = [(s.ident, s.data) for s in game.segments] + segments
    return game.raw[:0x16A] + b"".join(
        struct.pack("<HI", kind | (0x8000 if number == len(parts) - 1 else 0), len(data)) + data
        for number, (kind, data) in enumerate(parts))


class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (project.REPO / "build").mkdir(exist_ok=True)

    def test_pcm_wav_preserves_samples_and_padding(self):
        for channels, bits, samples in [(1, 8, b"\0\x80\xff"),
                                         (1, 16, b"\0\x80\xff\x7f"),
                                         (2, 16, b"\0\x80\xff\x7f\x34\x12\xff\xff")]:
            with self.subTest(channels=channels, bits=bits):
                output, suffix, info = audio.decode_audio(pcm(samples, channels, bits), "sound")
                self.assertEqual(suffix, "wav")
                with wave.open(io.BytesIO(output), "rb") as wav:
                    self.assertEqual(wav.getparams()[:3], (channels, bits // 8, 11025))
                    self.assertEqual(wav.getnframes(), len(samples) // (channels * bits // 8))
                    self.assertEqual(wav.readframes(wav.getnframes()), samples)
                self.assertEqual(info["sample_sha256"], hashlib.sha256(samples).hexdigest())
                self.assertEqual(struct.unpack_from("<I", output, 4)[0], len(output) - 8)
                self.assertEqual(struct.unpack_from("<I", output, 40)[0], len(samples))
                self.assertEqual(output[44:44 + len(samples)], samples)
                self.assertEqual(len(output) % 2, 0)

    def test_pcm_invalid_headers_sizes_and_alignment(self):
        base = pcm()
        mutations = [(6, "<I", 0), (30, "<H", 2), (32, "<H", 2),
                     (34, "<H", 3), (36, "<I", 0), (40, "<I", 3),
                     (44, "<H", 2), (46, "<H", 24)]
        invalid = [base[:31], base[:-1], pcm(b"x", bits=16)]
        for offset, form, value in mutations:
            changed = bytearray(base)
            struct.pack_into(form, changed, offset, value)
            invalid.append(bytes(changed))
        for data in invalid:
            with self.subTest(data=data[:48]):
                with self.assertRaises(project.InputError):
                    audio.decode_audio(data, "sound")

    def test_midi_exact_bytes_and_chunk_validation(self):
        raw = midi()
        output, suffix, info = audio.decode_audio(audio_record(2, raw), "music")
        self.assertEqual(output, raw)
        self.assertEqual(suffix, "mid")
        self.assertEqual(info, {"format": 0, "tracks": 1, "ticks_per_quarter": 96})
        bad = [raw[:13], raw[:-1], raw + b"extra", b"nope" + raw[4:],
               raw[:14] + b"nope" + raw[18:]]
        for offset, form, value in [(4, ">I", 7), (8, ">H", 3), (10, ">H", 0),
                                     (10, ">H", 2), (12, ">H", 0), (12, ">H", 0xE728),
                                     (18, ">I", 1000)]:
            changed = bytearray(raw)
            struct.pack_into(form, changed, offset, value)
            bad.append(bytes(changed))
        for data in bad:
            with self.subTest(data=data[:22]):
                with self.assertRaises(project.InputError):
                    audio.decode_audio(audio_record(2, data), "music")
        with self.assertRaises(project.InputError):
            audio.decode_audio(audio_record(1, raw), "music")

    def test_whole_bundle_repeat_fault_cleanup_and_refused_changes(self):
        manifest = {"source": {"sha256": "a" * 64}}
        files = {"manifest.json": b"{}\n", "sound-0-3.wav": b"synthetic"}
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            with patch.object(Path, "rename", side_effect=OSError):
                with self.assertRaises(OSError):
                    audio.save_bundle(manifest, files, repo)
            parent = repo / "export" / ("a" * 64)
            self.assertEqual(list(parent.iterdir()), [])
            with patch.object(Path, "write_bytes", side_effect=OSError):
                with self.assertRaises(OSError):
                    audio.save_bundle(manifest, files, repo)
            self.assertEqual(list(parent.iterdir()), [])
            target = audio.save_bundle(manifest, files, repo)
            self.assertEqual(audio.save_bundle(manifest, files, repo), target)
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, {**files, "sound-0-3.wav": b"changed"}, repo)
            self.assertEqual((target / "sound-0-3.wav").read_bytes(), b"synthetic")
            (target / "extra").write_bytes(b"extra")
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, files, repo)

    def test_symlink_directories_and_files_are_refused(self):
        manifest = {"source": {"sha256": "a" * 64}}
        files = {"manifest.json": b"keep"}
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            outside = repo / "outside"
            outside.mkdir()
            root = repo / "export"
            root.symlink_to(outside)
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, files, repo)
            root.unlink()
            root.mkdir()
            directory = root / ("a" * 64)
            directory.symlink_to(outside)
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, files, repo)
            directory.unlink()
            directory.mkdir()
            target = directory / "audio-v1"
            target.symlink_to(outside)
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, files, repo)
            target.unlink()
            target = audio.save_bundle(manifest, files, repo)
            victim = outside / "victim"
            victim.write_bytes(b"keep")
            (target / "manifest.json").unlink()
            (target / "manifest.json").symlink_to(victim)
            with self.assertRaises(project.InputError):
                audio.save_bundle(manifest, files, repo)
            self.assertEqual(victim.read_bytes(), b"keep")

    def test_cli_fault_classification(self):
        argv = ["audio_dump", "unused", "--klikback-src", "unused"]
        with patch.object(audio.sys, "argv", argv), patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad input")), \
                    patch.object(audio, "save_bundle") as save:
                self.assertEqual(audio.main(), 2)
                save.assert_not_called()
                report.assert_not_called()
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""), \
                    patch.object(audio, "audio_bundle", return_value=({}, {})), \
                    patch.object(audio, "save_bundle", side_effect=OSError("private path")):
                self.assertEqual(audio.main(), 1)
                report.assert_called_once_with("OSError", version=audio.VERSION,
                                               title="Audio exporter crashed")


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class AudioContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_slots_multiple_banks_and_missing_banks(self):
        manifest, files = audio.audio_bundle(self.reader, synthetic_project())
        self.assertEqual(manifest["banks"], [])
        self.assertEqual(set(files), {"manifest.json"})
        raw = with_banks(self.reader, [(13, bank({1: pcm(), 4: pcm(b"\0\x80", bits=16)})),
                                       (12, bank({2: audio_record(2, midi())})), (13, bank({1: pcm()})),
                                       (12, bank({}))])
        manifest, files = audio.audio_bundle(self.reader, raw)
        self.assertEqual([[e["id"] for e in b["entries"]] for b in manifest["banks"]],
                         [[1, 4], [2], [1], []])
        names = [e["file"] for b in manifest["banks"] for e in b["entries"]]
        self.assertEqual(len(set(names)), 4)
        self.assertEqual(json.loads(files["manifest.json"]), manifest)
        self.assertEqual(audio.audio_bundle(self.reader, raw), (manifest, files))
        invalid = with_banks(self.reader, [(13, bank({0: pcm(), 1: b"bad"}))])
        with self.assertRaises(project.InputError):
            audio.audio_bundle(self.reader, invalid)
        with patch.object(audio.sys, "argv", ["audio_dump", "unused", "--klikback-src",
                                              os.environ["FF_KLIKBACK_SRC"]]), \
                patch.object(Path, "read_bytes", return_value=invalid), \
                patch.object(audio, "save_bundle") as save, \
                patch.object(project, "report_fault") as report:
            self.assertEqual(audio.main(), 2)
            save.assert_not_called()
            report.assert_not_called()

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_samples_and_midi_match_source_exactly(self):
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        manifest, files = audio.audio_bundle(self.reader, raw)
        self.assertEqual({b["kind"]: [e["id"] for e in b["entries"]] for b in manifest["banks"]},
                         {"music": [0, 1], "sound": list(range(10)) + [11, 12, 13, 14, 16, 17, 18]})
        for b in manifest["banks"]:
            segment = game.segments[b["segment_id"]]
            # Read the bank table directly, independently of the bundle's offsets.
            for entry in b["entries"]:
                at, size = struct.unpack_from("<II", segment.data, 4 + entry["id"] * 8)
                record = segment.data[at:at + size]
                output = files[entry["file"]]
                self.assertEqual(entry["record_sha256"], hashlib.sha256(record).hexdigest())
                self.assertEqual(entry["file_sha256"], hashlib.sha256(output).hexdigest())
                if b["kind"] == "music":
                    self.assertEqual(output, record[32:])
                else:
                    with wave.open(io.BytesIO(output), "rb") as wav:
                        self.assertEqual(wav.readframes(wav.getnframes()), record[48:])
                        self.assertEqual(wav.getnchannels(), struct.unpack_from("<H", record, 34)[0])
                        self.assertEqual(wav.getframerate(), struct.unpack_from("<I", record, 36)[0])
                        self.assertEqual(wav.getsampwidth() * 8, struct.unpack_from("<H", record, 46)[0])
        self.assertEqual(audio.audio_bundle(self.reader, path.read_bytes()), (manifest, files))
        self.assertEqual(path.read_bytes(), raw)
