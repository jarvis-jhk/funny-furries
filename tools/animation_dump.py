#!/usr/bin/env python3
"""Export CnC active animation slots, directions and image handles without runtime guesses."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import project_index as project

VERSION = "animation-dump/1"


def decode_active(data):
    if len(data) < 48 or data[42:46] != b"SPRI":
        raise project.InputError("unsupported active object signature or truncated sprite header")
    sprite_bytes = int.from_bytes(data[46:48], "little")
    base = 46 + sprite_bytes
    if sprite_bytes < 2 or base + 36 > len(data):
        raise project.InputError("sprite extent leaves no complete animation table")
    extent = int.from_bytes(data[base:base + 2], "little")
    end = base + extent
    if extent < 36 or end > len(data):
        raise project.InputError("animation region length is invalid")
    spans = {(base, base + 36): "animation-header"}

    def span(start, size, kind):
        if start < base + 36 or start + size > end:
            raise project.InputError("animation pointer or count is outside its region")
        key = (start, start + size)
        if key in spans and spans[key] != kind:
            raise project.InputError("animation structures alias incompatible records")
        spans[key] = kind

    animations = []
    for slot, pointer in enumerate(struct.unpack_from("<16H", data, base + 4)):
        entry = {"id": slot, "pointer_raw_u16": pointer, "offset": None, "directions": None}
        if pointer < 0x8000:
            if pointer < 36:
                raise project.InputError("animation pointer enters its header")
            at = base + pointer
            span(at, 64, "direction-table")
            directions = []
            for direction, dp in enumerate(struct.unpack_from("<32H", data, at)):
                out = {"id": direction, "pointer_raw_u16": dp, "offset": None,
                       "header_hex": None, "image_ids": None}
                if dp < 0x8000:
                    if dp < 64:
                        raise project.InputError("direction pointer enters its table")
                    dt = at + dp
                    if dt + 8 > end:
                        raise project.InputError("direction header is truncated")
                    count = int.from_bytes(data[dt + 6:dt + 8], "little")
                    span(dt, 8 + 2 * count, "direction-record")
                    out.update(offset=dt, header_hex=data[dt:dt + 8].hex(),
                               image_ids=list(struct.unpack_from(f"<{count}H", data, dt + 8)))
                directions.append(out)
            entry.update(offset=at, directions=directions)
        animations.append(entry)
    last = base
    opaque = []
    for start, stop in sorted(spans):
        if start < last:
            raise project.InputError("animation records partially overlap")
        if start > last:
            opaque.append({"offset": last, "raw_hex": data[last:start].hex()})
        last = stop
    if last < end:
        opaque.append({"offset": last, "raw_hex": data[last:end].hex()})
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "raw_hex": data.hex(), "sprite_bytes": sprite_bytes,
            "animation_offset": base, "animation_bytes": extent,
            "header_hex": data[base:base + 4].hex(), "animations": animations,
            "opaque_animation_spans": opaque, "prefix_hex": data[:base].hex(),
            "tail_hex": data[end:].hex()}


def animation_document(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    banks = [{"segment_id": i, "offset": s.offset,
              "slots": [slot for slot, _, _ in reader.walk_bank(s.data)]}
             for i, s in enumerate(game.segments) if s.ident == 10]
    available = {slot for bank in banks for slot in bank["slots"]}

    def objects(data, global_list=False):
        result = []
        for obj in reader.object_definitions(data, globals_have_blocks=global_list):
            blocks = []
            if obj.object_type == 2:
                for block_id, block in enumerate(obj.blocks):
                    if block.ident != 0:
                        continue
                    decoded = decode_active(block.data)
                    for anim in decoded["animations"]:
                        for direction in anim["directions"] or []:
                            if any(image not in available for image in direction["image_ids"] or []):
                                raise project.InputError("animation references an unoccupied image handle")
                    blocks.append({"block_id": block_id, "object_list_offset": block.offset,
                                   **decoded})
            result.append({"id": obj.index, "type": obj.object_type, "global": obj.is_global,
                           "deleted": obj.deleted, "active_data": blocks})
        return result

    globals_ = [{"segment_id": i, "offset": s.offset, "objects": objects(s.data, True)}
                for i, s in enumerate(game.segments) if s.ident == 6]
    frames = [{"id": i, "object_lists": [
        {"block_id": j, "frame_offset": b.offset, "objects": objects(b.data)}
        for j, b in enumerate(reader.level_blocks(level.data)[1]) if b.ident == 2]}
        for i, level in enumerate(game.levels())]
    return {"schema_version": 1, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "image_banks": banks, "global_object_lists": globals_, "frames": frames,
            "coverage": {"active_animation_storage": True, "image_handles": True,
                         "runtime_animation_semantics": False, "global_reference_resolution": False,
                         "other_object_images": False, "behaviour": False}}


def save_animations(document, repo=project.REPO):
    return project.save_export(document, json.dumps(
        document, ensure_ascii=True, indent=2, sort_keys=True) + "\n", "animations.json", repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            document = animation_document(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        print(save_animations(document).relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Animation exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
