#!/usr/bin/env python3
"""Export local CnC PCM/MIDI banks without redistributing game content."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import project_index as project

VERSION = "audio-dump/1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def midi_info(data):
    # Only the SMF container is interpreted. Events and instruments stay intact.
    if len(data) < 14 or data[:4] != b"MThd":
        raise project.InputError("expected a Standard MIDI File header")
    size, form, tracks, division = struct.unpack_from(">IHHH", data, 4)
    if size != 6 or form not in (0, 1, 2) or not tracks or (form == 0 and tracks != 1):
        raise project.InputError("unsupported MIDI header or track count")
    if not division or division & 0x8000:
        raise project.InputError("only MIDI ticks-per-quarter timing is supported")
    cursor = 14
    for _ in range(tracks):
        if cursor + 8 > len(data) or data[cursor:cursor + 4] != b"MTrk":
            raise project.InputError("missing MIDI track header")
        length = struct.unpack_from(">I", data, cursor + 4)[0]
        cursor += 8 + length
        if cursor > len(data):
            raise project.InputError("MIDI track exceeds its record")
    if cursor != len(data):
        raise project.InputError("MIDI track count leaves trailing bytes")
    return {"format": form, "tracks": tracks, "ticks_per_quarter": division}


def decode_audio(data, kind):
    if len(data) < 32 or struct.unpack_from("<I", data, 6)[0] != len(data) - 32:
        raise project.InputError("audio record length disagrees with its bank entry")
    stored_kind = struct.unpack_from("<H", data, 30)[0]
    if kind == "music" and stored_kind == 2:
        payload = data[32:]
        return payload, "mid", midi_info(payload)
    if kind != "sound" or stored_kind != 1 or len(data) < 48:
        raise project.InputError("unsupported CnC audio record kind")
    form, channels, rate, byte_rate, alignment, bits = struct.unpack_from("<HHIIHH", data, 32)
    if form != 1 or channels not in (1, 2) or bits not in (8, 16) or not rate:
        raise project.InputError("only mono/stereo 8/16-bit PCM is supported")
    if alignment != channels * (bits // 8) or byte_rate != rate * alignment:
        raise project.InputError("PCM format has inconsistent rate/alignment")
    samples = data[48:]
    if len(samples) % alignment:
        raise project.InputError("PCM payload ends in a partial sample frame")
    # RIFF chunk sizes exclude their even-byte padding; sample bytes never change.
    body = b"WAVEfmt " + struct.pack("<I", 16) + data[32:48]
    body += b"data" + struct.pack("<I", len(samples)) + samples
    if len(samples) % 2:
        body += b"\0"
    wav = b"RIFF" + struct.pack("<I", len(body)) + body
    return wav, "wav", {"channels": channels, "sample_rate": rate,
                        "bits_per_sample": bits, "sample_frames": len(samples) // alignment,
                        "sample_sha256": digest(samples)}


def audio_bundle(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    files, banks = {}, []
    for segment_id, segment in enumerate(game.segments):
        kind = reader.BANK_SEGMENTS.get(segment.ident)
        if kind not in ("sound", "music"):
            continue
        entries = []
        for slot, offset, size in reader.walk_bank(segment.data):
            record = segment.data[offset:offset + size]
            payload, suffix, info = decode_audio(record, kind)
            # Segment position disambiguates repeated banks; filenames never use names.
            filename = f"{kind}-{segment_id}-{slot}.{suffix}"
            files[filename] = payload
            entries.append({"id": slot, "offset": offset, "bytes": size,
                            "header_hex": record[:32].hex(), "record_sha256": digest(record),
                            "file": filename, "file_bytes": len(payload),
                            "file_sha256": digest(payload), "audio": info})
        banks.append({"segment_id": segment_id, "id": segment.ident, "kind": kind,
                      "entries": entries})
    manifest = {"schema_version": 1, "exporter": VERSION, "source": inventory["source"],
                "reader_sha256": inventory["reader_sha256"], "banks": banks,
                "coverage": {"pcm_wav_files": True, "midi_files": True,
                             "midi_event_semantics": False, "images": False,
                             "arena_geometry": False, "behaviour": False}}
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return manifest, files


def save_bundle(manifest, files, repo=project.REPO):
    root = repo / "export"
    directory = root / manifest["source"]["sha256"]
    target = directory / "audio-v1"
    if any(path.is_symlink() for path in (root, directory, target)):
        raise project.InputError("audio output directories must not be symlinks")
    directory.mkdir(parents=True, exist_ok=True)
    # A whole immutable bundle is installed once, so a failed write cannot mix
    # an old manifest with new audio. Repeat runs must verify the complete tree.
    if target.exists():
        if not target.is_dir() or {p.name for p in target.iterdir()} != set(files):
            raise project.InputError("existing audio bundle differs; move it aside first")
        for name, payload in files.items():
            path = target / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise project.InputError("existing audio bundle differs; move it aside first")
        return target
    with tempfile.TemporaryDirectory(dir=directory, prefix=".audio-") as scratch:
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
            manifest, files = audio_bundle(reader, args.project.read_bytes())
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
        project.report_fault(type(error).__name__, version=VERSION, title="Audio exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
