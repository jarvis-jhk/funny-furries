#!/usr/bin/env python3
"""Inventory a local, unprotected CnC project without distributing its content."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

VERSION = "project-index/1"
REPO = Path(__file__).resolve().parents[1]


class InputError(ValueError):
    pass


def load_reader(source: Path):
    module = source / "klikback/core/tgf/format.py"
    if not module.is_file():
        raise InputError("--klikback-src must contain klikback/core/tgf/format.py")
    sys.path.insert(0, str(source.resolve()))
    reader = importlib.import_module("klikback.core.tgf.format")
    if Path(reader.__file__).resolve() != module.resolve():
        raise InputError("a different KlikBack reader is already loaded")
    return reader


def object_index(reader, data: bytes, *, global_list=False):
    # The upstream reader tolerates a missing count and trailing object bytes.
    # An inventory must not silently call those complete.
    if len(data) < 4:
        raise InputError("object list has no complete header")
    objects = reader.object_definitions(data, globals_have_blocks=global_list)
    end = objects[-1].offset if objects else 4
    if end != len(data):
        raise InputError("object list has unparsed trailing bytes")
    return [{"id": o.index, "name": o.name, "type": o.object_type,
             "type_name": o.type_name, "flags": o.flags,
             "global": o.is_global, "deleted": o.deleted,
             "offset": o.base,
             "blocks": [{"id": b.ident, "offset": b.offset,
                         "bytes": len(b.data)} for b in o.blocks]}
            for o in objects]


def inventory(reader, raw: bytes):
    game = reader.read(raw)
    if game.protected:
        raise InputError("use an unprotected/decompiled project")
    if game.family != "cnc":
        raise InputError("this exporter supports CnC projects only")
    levels = game.levels()
    if len(levels) != game.level_count:
        raise InputError("level count disagrees with the segment list")
    if game.level_addresses != [s.offset + 6 for s in levels]:
        raise InputError("level address table disagrees with segment order")
    frames = []
    for number, segment in enumerate(levels):
        start, blocks = reader.level_blocks(segment.data)
        frames.append({"id": number, "offset": segment.offset,
                       "bytes": len(segment.data), "blocks_start": start,
                       "blocks": [{"id": b.ident, "name": b.name,
                                   "offset": b.offset, "bytes": len(b.data)}
                                  for b in blocks],
                       "object_lists": [object_index(reader, b.data)
                                        for b in blocks if b.ident == 2]})
    banks = []
    for segment in game.segments:
        if segment.ident in reader.BANK_SEGMENTS:
            banks.append({"id": segment.ident, "kind": reader.BANK_SEGMENTS[segment.ident],
                          "entries": [{"id": slot, "offset": offset, "bytes": size}
                                      for slot, offset, size in reader.walk_bank(segment.data)]})
    return {"schema_version": 1, "exporter": VERSION,
            "source": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                       "signature": game.signature.decode("ascii"), "version": game.version},
            "reader_sha256": hashlib.sha256(Path(reader.__file__).read_bytes()).hexdigest(),
            "coverage": {"inventory": True, "event_semantics": False,
                         "asset_files": False, "arena_geometry": False},
            "segments": [{"id": s.ident, "name": s.name, "offset": s.offset,
                          "bytes": len(s.data)} for s in game.segments],
            "global_object_lists": [object_index(reader, s.data, global_list=True)
                                    for s in game.segments if s.ident == 6],
            "frames": frames, "banks": banks}


def save_index(document, repo=REPO):
    payload = json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    return save_export(document, payload, "project-index.json", repo)


def save_export(document, payload, filename, repo=REPO):
    export_root = repo / "export"
    directory = export_root / document["source"]["sha256"]
    # Generated data must never overwrite tracked sources or escape via symlinks.
    if export_root.is_symlink() or directory.is_symlink():
        raise InputError("export directories must not be symlinks")
    directory.mkdir(parents=True, exist_ok=True)
    if filename not in {"project-index.json", "events.json", "events.txt", "frame-layout.json", "animations.json", "backdrops.json", "displays.json"}:
        raise InputError("unsupported export filename")
    target = directory / filename
    if target.is_symlink():
        raise InputError("export target must not be a symlink")
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         prefix=".index-", delete=False) as stream:
            name = stream.name
            stream.write(payload)
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return target


def report_fault(error_type, *, version=VERSION, title="Project index exporter crashed"):
    url = os.environ.get("FF_FAULT_REPORT_URL")
    if not url:
        return
    # Detached delivery has a short timeout. Only fixed context and exception type
    # leave the process; paths, original content and exception messages stay local.
    payload = json.dumps({"lane": "furries", "kind": "bug",
                          "title": title,
                          "detail": error_type,
                          "source": f"funny-furries {version} {sys.platform}"})
    try:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--deliver-fault",
                          url, payload], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = load_reader(args.klikback_src)
            document = inventory(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        print(save_index(document).relative_to(REPO))
        return 0
    except InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        report_fault(type(error).__name__)
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--deliver-fault":
        from urllib.request import Request, urlopen
        try:
            request = Request(sys.argv[2], data=sys.argv[3].encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=2):
                pass
        except Exception:
            pass
    else:
        sys.exit(main())
