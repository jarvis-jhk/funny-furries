#!/usr/bin/env python3
"""Export CnC backdrop header artwork, retaining unknown geometry and runtime fields."""
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

VERSION = "backdrop-dump/2"
HEADER_BYTES = 68


def decode_header(head):
    if len(head) != HEADER_BYTES or head[42] not in (0, 1):
        raise project.InputError("unsupported backdrop header size or object type")
    image = int.from_bytes(head[54:56], "little")
    artwork = {"kind": "image", "image_id": image}
    if head[42] == 0:
        fill = head[32]
        # These are editor-art fields. They do not establish collision, shape,
        # dimensions or how a runtime paints a placed quick backdrop.
        if fill & ~0x1F or fill & 15 not in (0, 1, 2):
            raise project.InputError("unsupported quick backdrop fill flags")
        kind = {0: "solid", 1: "mosaic", 2: "gradient"}[fill & 15]
        colors = []
        for at in (24, 28):
            value = int.from_bytes(head[at:at + 4], "little")
            colors.append({"raw_u32": value,
                           "rgb": [value & 255, (value >> 8) & 255, (value >> 16) & 255]})
        artwork = {"kind": kind, "fill_raw_u8": fill, "colors": colors,
                   "image_id": image if kind == "mosaic" else None,
                   "gradient_axis": ("horizontal" if fill & 16 else "vertical")
                   if kind == "gradient" else None}
    # Original header-to-placement refresh copies these quick-backdrop words;
    # rendering bounds consumers sign-extend them. Ordinary backdrops instead
    # query image metadata, so their same-offset header words stay opaque.
    dimensions = None
    if head[42] == 0:
        dimensions = {"meaning": "quick_backdrop_dimension_inputs",
            "evidence": "original_runtime_header_refresh_and_rectangle_paths",
            "runtime_resolution": False,
            **{axis: {"header_offset": offset, "placement_offset": target,
                      "raw_u16": struct.unpack_from("<H", head, offset)[0],
                      "signed_i16": struct.unpack_from("<h", head, offset)[0]}
               for axis, offset, target in (("width", 34, 26), ("height", 36, 28))}}
    return {"header_bytes": len(head), "header_sha256": hashlib.sha256(head).hexdigest(),
            "header_hex": head.hex(), "image_word_raw_u16": image, "artwork": artwork,
            "quick_backdrop_dimension_inputs": dimensions}


def backdrop_document(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    banks = [{"segment_id": i, "offset": s.offset,
              "slots": [slot for slot, _, _ in reader.walk_bank(s.data)]}
             for i, s in enumerate(game.segments) if s.ident == 10]
    candidates = {}
    for bank in banks:
        for image in bank["slots"]:
            candidates.setdefault(image, []).append(bank["segment_id"])

    def objects(data, global_list=False):
        result = []
        for obj in reader.object_definitions(data, globals_have_blocks=global_list):
            decoded = None
            if obj.object_type in (0, 1):
                decoded = decode_header(data[obj.base:obj.base + HEADER_BYTES])
                image = decoded["artwork"]["image_id"]
                matches = candidates.get(image, []) if image is not None else []
                if image is not None and not matches:
                    raise project.InputError("backdrop references an unoccupied image handle")
                decoded["artwork"]["image_bank_candidates"] = matches
            result.append({"id": obj.index, "type": obj.object_type, "global": obj.is_global,
                           "deleted": obj.deleted, "object_list_offset": obj.base,
                           "backdrop": decoded})
        return result

    globals_ = [{"segment_id": i, "offset": s.offset, "objects": objects(s.data, True)}
                for i, s in enumerate(game.segments) if s.ident == 6]
    frames = [{"id": i, "object_lists": [
        {"block_id": j, "frame_offset": b.offset, "objects": objects(b.data)}
        for j, b in enumerate(reader.level_blocks(level.data)[1]) if b.ident == 2]}
        for i, level in enumerate(game.levels())]
    return {"schema_version": 2, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "image_banks": banks, "global_object_lists": globals_, "frames": frames,
            "coverage": {"backdrop_header_artwork": True, "image_handles": True,
                         "quick_backdrop_dimension_inputs": True,
                         "runtime_rendering": False, "global_reference_resolution": False,
                         "arena_geometry": False, "spawns": False, "behaviour": False}}


def save_backdrops(document, repo=project.REPO):
    return project.save_export(document, json.dumps(
        document, ensure_ascii=True, indent=2, sort_keys=True) + "\n", "backdrops.json", repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            document = backdrop_document(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        print(save_backdrops(document).relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Backdrop exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
