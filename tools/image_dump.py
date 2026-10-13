#!/usr/bin/env python3
"""Export supported local CnC truecolour image banks as RGBA PNG files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import project_index as project

VERSION = "image-dump/1"
MAX_PIXELS = 4_194_304


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode_image(data):
    if len(data) < 24:
        raise project.InputError("image has no complete header")
    length, width, height, mode, flags, hx, hy, ax, ay = struct.unpack_from("<IHHBB4H", data, 6)
    if length != len(data) - 24:
        raise project.InputError("image length disagrees with its bank record")
    # Only the two shapes present in the local original are established here.
    # Reject other modes rather than guess palette or colour-key semantics.
    if mode != 4 or flags not in (0x40, 0x44):
        raise project.InputError("only mode4 TGF truecolour, raw or RLE4, is supported")
    if not width or not height or width * height > MAX_PIXELS:
        raise project.InputError("image dimensions are empty or exceed the pixel limit")
    payload = data[24:]
    if len(payload) < 4 + 8 * height:
        raise project.InputError("image has a truncated pointer table")
    bufsize = struct.unpack_from("<I", payload)[0]
    pointers = [struct.unpack_from("<II", payload, 4 + 8 * line) for line in range(height)]
    pair_start = 8 * height
    colour_base = pointers[0][1]
    colour_size = bufsize - 4 - colour_base
    colour_at = 4 + colour_base
    if pointers[0][0] != pair_start or colour_base < pair_start or colour_size < 0 \
            or colour_size % 3 or colour_at > len(payload) or colour_size > width * height * 3:
        raise project.InputError("image buffer and pointer table disagree")
    lines = []
    for line, (start, colour) in enumerate(pointers):
        end, cend = pointers[line + 1] if line + 1 < height else (colour_base, bufsize - 4)
        if not pair_start <= start <= end <= colour_base or (end - start) % 2 \
                or not colour_base <= colour <= cend <= bufsize - 4:
            raise project.InputError("image row pointers are out of bounds")
        pairs = list(zip(payload[4 + start:4 + end:2], payload[5 + start:4 + end:2]))
        if sum(t + o for t, o in pairs) > width or sum(o for _, o in pairs) * 3 != cend - colour:
            raise project.InputError("image row runs disagree with width or colour pointers")
        lines.append(pairs)
    encoded = payload[colour_at:]
    if flags == 0x44:
        colours = bytearray()
        cursor = 0
        terminated = False
        while cursor < len(encoded):
            count = encoded[cursor]
            cursor += 1
            if count == 0:
                terminated = True
                break
            n = count & 0x7F
            size = n * 3 if count & 0x80 else 3
            if not n or cursor + size > len(encoded) or len(colours) + n * 3 > colour_size:
                raise project.InputError("image RLE run is empty, truncated or too long")
            chunk = encoded[cursor:cursor + size]
            colours.extend(chunk if count & 0x80 else chunk * n)
            cursor += size
        if not terminated or cursor != len(encoded):
            raise project.InputError("image RLE has no final terminator or has trailing bytes")
    else:
        padding = (-bufsize) % 4
        if len(encoded) != colour_size + padding or encoded[colour_size:] != bytes(padding):
            raise project.InputError("raw image buffer has invalid alignment padding")
        colours = encoded[:colour_size]
    if len(colours) != colour_size:
        raise project.InputError("image colour stream does not fill exactly its buffer")
    rgba = bytearray(width * height * 4)
    cursor = 0
    for y, pairs in enumerate(lines):
        x = 0
        for transparent, opaque in pairs:
            x += transparent
            for _ in range(opaque):
                b, g, r = colours[cursor:cursor + 3]
                at = (y * width + x) * 4
                rgba[at:at + 4] = bytes((r, g, b, 255))
                cursor += 3
                x += 1
    return bytes(rgba), {"width": width, "height": height, "mode": mode, "flags": flags,
                         "hot_spot_raw_u16": [hx, hy], "action_point_raw_u16": [ax, ay]}


def png(rgba, width, height):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    scanlines = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")


def image_bundle(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    files, banks = {}, []
    for segment_id, segment in enumerate(game.segments):
        if reader.BANK_SEGMENTS.get(segment.ident) != "image":
            continue
        entries = []
        for slot, offset, size in reader.walk_bank(segment.data):
            record = segment.data[offset:offset + size]
            rgba, info = decode_image(record)
            filename = f"image-{segment_id}-{slot}.png"
            payload = png(rgba, info["width"], info["height"])
            files[filename] = payload
            entries.append({"id": slot, "offset": offset, "bytes": size,
                            "header_hex": record[:24].hex(), "record_sha256": digest(record),
                            "file": filename, "file_bytes": len(payload), "file_sha256": digest(payload),
                            "rgba_sha256": digest(rgba), "image": info})
        banks.append({"segment_id": segment_id, "id": segment.ident, "entries": entries})
    manifest = {"schema_version": 1, "exporter": VERSION, "source": inventory["source"],
                "reader_sha256": inventory["reader_sha256"], "banks": banks,
                "coverage": {"mode4_tgf_rgba_png": True, "other_image_modes": False,
                             "animation_mapping": False, "arena_geometry": False, "behaviour": False}}
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return manifest, files


def save_bundle(manifest, files, repo=project.REPO):
    root = repo / "export"
    directory = root / manifest["source"]["sha256"]
    target = directory / "images-v1"
    if any(path.is_symlink() for path in (root, directory, target)):
        raise project.InputError("image output directories must not be symlinks")
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_dir() or {p.name for p in target.iterdir()} != set(files):
            raise project.InputError("existing image bundle differs; move it aside first")
        for name, payload in files.items():
            path = target / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise project.InputError("existing image bundle differs; move it aside first")
        return target
    # The manifest and every image become visible together; retries never repair
    # a changed bundle silently or leave a partial install after a write failure.
    with tempfile.TemporaryDirectory(dir=directory, prefix=".images-") as scratch:
        staging = Path(scratch) / "bundle"
        staging.mkdir()
        for name, payload in files.items():
            (staging / name).write_bytes(payload)
        staging.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            manifest, files = image_bundle(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        target = save_bundle(manifest, files)
        print(target.relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Image exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
