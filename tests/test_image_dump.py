import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from tools import image_dump as image
from tools import project_index as project
from test_audio_dump import bank
from test_project_index import synthetic_project


def record(compressed=False):
    # 3x2: transparent/red/blue, then green/transparent/transparent.
    pairs = b"\x01\x02\x00\x01"
    colours = b"\0\0\xff\xff\0\0\0\xff\0"
    bufsize = 4 + 16 + len(pairs) + len(colours)
    body = struct.pack("<I4I", bufsize, 16, 20, 18, 26) + pairs
    body += b"\x83" + colours + b"\0" if compressed else colours + bytes((-bufsize) % 4)
    return struct.pack("<HIIHHBB4H", 13, 2, len(body), 3, 2, 4,
                       0x44 if compressed else 0x40, 65535, 7, 9, 65534) + body


EXPECTED = bytes((0, 0, 0, 0, 255, 0, 0, 255, 0, 0, 255, 255,
                  0, 255, 0, 255, 0, 0, 0, 0, 0, 0, 0, 0))


def read_png(data):
    # Independent chunk/CRC and scanline readback, without the PNG writer.
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    cursor, chunks = 8, []
    while cursor < len(data):
        length = struct.unpack_from(">I", data, cursor)[0]
        kind = data[cursor + 4:cursor + 8]
        body = data[cursor + 8:cursor + 8 + length]
        crc = struct.unpack_from(">I", data, cursor + 8 + length)[0]
        assert zlib.crc32(kind + body) == crc
        chunks.append((kind, body))
        cursor += 12 + length
    assert cursor == len(data) and [c[0] for c in chunks] == [b"IHDR", b"IDAT", b"IEND"]
    w, h, depth, colour, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    assert (depth, colour, compression, filtering, interlace) == (8, 6, 0, 0, 0)
    scanlines = zlib.decompress(chunks[1][1])
    stride = 1 + w * 4
    assert len(scanlines) == stride * h
    assert all(scanlines[y * stride] == 0 for y in range(h))
    return w, h, b"".join(scanlines[y * stride + 1:(y + 1) * stride] for y in range(h))


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (project.REPO / "build").mkdir(exist_ok=True)

    def test_raw_rle_colours_transparency_metadata_png(self):
        for compressed in (False, True):
            rgba, info = image.decode_image(record(compressed))
            self.assertEqual(rgba, EXPECTED)
            self.assertEqual(info["hot_spot_raw_u16"], [65535, 7])
            self.assertEqual(info["action_point_raw_u16"], [9, 65534])
            self.assertEqual(read_png(image.png(rgba, 3, 2)), (3, 2, EXPECTED))
        # Explicit transparency differs from an opaque black pixel; repeated RLE
        # must not consume more input bytes than the single colour it repeats.
        raw = bytearray(record(True))
        raw[48:] = b"\x03\0\0\0\0"
        struct.pack_into("<I", raw, 6, len(raw) - 24)
        rgba, _ = image.decode_image(bytes(raw))
        self.assertEqual(rgba[4:8], b"\0\0\0\xff")
        self.assertEqual(rgba[:4], b"\0\0\0\0")

    def test_invalid_headers_pointers_runs_padding_and_trailing_bytes(self):
        bad = [b"", record()[:23], record()[:-1], record() + b"extra"]
        for offset, form, value in [(6, "<I", 0), (10, "<H", 0), (12, "<H", 0),
                                     (14, "B", 6), (15, "B", 0x41),
                                     (24, "<I", 2), (28, "<I", 15), (32, "<I", 15),
                                     (36, "<I", 15), (40, "<I", 25), (44, "B", 4),
                                     (45, "B", 1), (len(record()) - 1, "B", 1)]:
            raw = bytearray(record())
            struct.pack_into(form, raw, offset, value)
            bad.append(bytes(raw))
        oversized = bytearray(record())
        struct.pack_into("<HH", oversized, 10, 65535, 65535)
        bad.append(bytes(oversized))
        for encoded in [b"\x80\0", b"\x03\0", b"\x04\0\0\0\0", b"\x83" + bytes(9),
                        b"\x83" + bytes(9) + b"\0extra", b"\0"]:
            raw = bytearray(record(True)[:48] + encoded)
            struct.pack_into("<I", raw, 6, len(raw) - 24)
            bad.append(bytes(raw))
        for raw in bad:
            with self.subTest(raw=raw.hex()):
                with self.assertRaises(project.InputError):
                    image.decode_image(raw)

    def test_atomic_bundle_repeat_changed_extra_missing_and_fault_cleanup(self):
        manifest = {"source": {"sha256": "a" * 64}}
        files = {"manifest.json": b"{}", "image-0-2.png": b"synthetic"}
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            for operation in ("rename", "write_bytes"):
                with patch.object(Path, operation, side_effect=OSError):
                    with self.assertRaises(OSError):
                        image.save_bundle(manifest, files, repo)
                self.assertEqual(list((repo / "export" / ("a" * 64)).iterdir()), [])
            target = image.save_bundle(manifest, files, repo)
            self.assertEqual(image.save_bundle(manifest, files, repo), target)
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, {**files, "manifest.json": b"changed"}, repo)
            self.assertEqual((target / "manifest.json").read_bytes(), b"{}")
            (target / "extra").write_bytes(b"extra")
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)
            (target / "extra").unlink()
            (target / "manifest.json").unlink()
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)

    def test_symlink_directories_and_files_refused(self):
        manifest = {"source": {"sha256": "a" * 64}}
        files = {"manifest.json": b"keep"}
        with tempfile.TemporaryDirectory(dir=project.REPO / "build") as scratch:
            repo = Path(scratch)
            outside = repo / "outside"
            outside.mkdir()
            root = repo / "export"
            root.symlink_to(outside)
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)
            root.unlink()
            root.mkdir()
            directory = root / ("a" * 64)
            directory.symlink_to(outside)
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)
            directory.unlink()
            directory.mkdir()
            target = directory / "images-v1"
            target.symlink_to(outside)
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)
            target.unlink()
            target = image.save_bundle(manifest, files, repo)
            victim = outside / "victim"
            victim.write_bytes(b"keep")
            (target / "manifest.json").unlink()
            (target / "manifest.json").symlink_to(victim)
            with self.assertRaises(project.InputError):
                image.save_bundle(manifest, files, repo)
            self.assertEqual(victim.read_bytes(), b"keep")

    def test_cli_fault_classification(self):
        argv = ["image_dump", "unused", "--klikback-src", "unused"]
        with patch.object(image.sys, "argv", argv), patch.object(project, "report_fault") as report:
            with patch.object(project, "load_reader", side_effect=project.InputError("bad input")), \
                    patch.object(image, "save_bundle") as save:
                self.assertEqual(image.main(), 2)
                save.assert_not_called()
                report.assert_not_called()
            with patch.object(project, "load_reader"), patch.object(Path, "read_bytes", return_value=b""), \
                    patch.object(image, "image_bundle", return_value=({}, {})), \
                    patch.object(image, "save_bundle", side_effect=OSError("private path")):
                self.assertEqual(image.main(), 1)
                report.assert_called_once_with("OSError", version=image.VERSION, title="Image exporter crashed")


@unittest.skipUnless(os.environ.get("FF_KLIKBACK_SRC"), "set FF_KLIKBACK_SRC for parser tests")
class ImageContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ["FF_KLIKBACK_SRC"]))

    def test_gap_repeated_empty_missing_banks_and_late_invalid_record(self):
        def image_project(banks):
            game = self.reader.read(synthetic_project())
            parts = [(s.ident, s.data) for s in game.segments if s.ident != 10] + banks
            return game.raw[:0x16A] + b"".join(
                struct.pack("<HI", kind | (0x8000 if i == len(parts) - 1 else 0), len(data)) + data
                for i, (kind, data) in enumerate(parts))
        manifest, files = image.image_bundle(self.reader, image_project([]))
        self.assertEqual(manifest["banks"], [])
        self.assertEqual(set(files), {"manifest.json"})
        raw = image_project([(10, bank({1: record(), 4: record(True)})),
                             (10, bank({1: record()})), (10, bank({}))])
        manifest, files = image.image_bundle(self.reader, raw)
        self.assertEqual([[e["id"] for e in b["entries"]] for b in manifest["banks"]],
                         [[1, 4], [1], []])
        self.assertEqual(len(files), 4)
        self.assertEqual(json.loads(files["manifest.json"]), manifest)
        self.assertEqual(image.image_bundle(self.reader, raw), (manifest, files))
        bad = image_project([(10, bank({0: record(), 1: b"bad"}))])
        with patch.object(image.sys, "argv", ["image_dump", "unused", "--klikback-src",
                                               os.environ["FF_KLIKBACK_SRC"]]), \
                patch.object(Path, "read_bytes", return_value=bad), \
                patch.object(image, "save_bundle") as save, \
                patch.object(project, "report_fault") as report:
            self.assertEqual(image.main(), 2)
            save.assert_not_called()
            report.assert_not_called()

    @unittest.skipUnless(os.environ.get("FF_TEST_PROJECT"), "set FF_TEST_PROJECT for original verification")
    def test_original_all_png_pixels_against_external_decoder_and_source_table(self):
        from klikback.core.tgf import image as oracle
        path = Path(os.environ["FF_TEST_PROJECT"])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        manifest, files = image.image_bundle(self.reader, raw)
        self.assertEqual(sum(len(b["entries"]) for b in manifest["banks"]), 614)
        flags = {}
        for bank_info in manifest["banks"]:
            segment = game.segments[bank_info["segment_id"]]
            for entry in bank_info["entries"]:
                offset, size = struct.unpack_from("<II", segment.data, 4 + entry["id"] * 8)
                rec = segment.data[offset:offset + size]
                decoded = oracle.parse_record(rec)
                flags[decoded.flags] = flags.get(decoded.flags, 0) + 1
                expected = bytearray()
                for row in oracle.decode_rows(decoded):
                    for value in row:
                        expected.extend(b"\0\0\0\0" if value is None else
                                        bytes((value >> 16 & 255, value >> 8 & 255, value & 255, 255)))
                w, h, rgba = read_png(files[entry["file"]])
                self.assertEqual((w, h), (decoded.width, decoded.height))
                self.assertTrue(rgba == bytes(expected), f"RGBA differs at bank slot {entry['id']}")
                self.assertEqual(entry["rgba_sha256"], hashlib.sha256(expected).hexdigest())
                self.assertEqual(entry["record_sha256"], hashlib.sha256(rec).hexdigest())
                self.assertEqual(entry["image"]["hot_spot_raw_u16"], list(decoded.hot_spot))
                self.assertEqual(entry["image"]["action_point_raw_u16"], list(decoded.action_point))
        self.assertEqual(flags, {0x40: 10, 0x44: 604})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(image.image_bundle(self.reader, raw), (manifest, files))
