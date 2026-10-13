#!/usr/bin/env python3
"""Export CnC score/lives/counter artwork sections without guessing numeric rendering."""
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

VERSION = "display-dump/1"
SIGNATURES = {5: b"SCRE", 6: b"LIVE", 7: b"CNTR"}


def decode_display(data, object_type):
    signature = SIGNATURES.get(object_type)
    if signature is None or len(data) < 48 or data[42:46] != signature:
        raise project.InputError("unsupported display signature or truncated header")
    cursor = 46
    attributes = None
    if object_type == 7:
        size = int.from_bytes(data[cursor:cursor + 2], "little")
        if size < 2 or cursor + size > len(data):
            raise project.InputError("counter attribute extent is invalid")
        attributes = {"offset": cursor, "bytes": size,
                      "raw_hex": data[cursor:cursor + size].hex()}
        cursor += size
    sections = []
    while cursor < len(data):
        if cursor + 4 > len(data):
            raise project.InputError("display section header is truncated")
        size, kind = struct.unpack_from("<HH", data, cursor)
        if size < 4 or cursor + size > len(data):
            raise project.InputError("display section extent is invalid")
        section = data[cursor:cursor + size]
        images = None
        # Only image-list modes supported by independent editor-art evidence are
        # interpreted. A word in an opaque bar/text/other mode is not an image.
        if kind in (1, 4):
            if size < 8:
                raise project.InputError("image display header is truncated")
            count = int.from_bytes(section[6:8], "little")
            if size != 8 + 2 * count:
                raise project.InputError("display image count disagrees with section length")
            images = list(struct.unpack_from(f"<{count}H", section, 8))
        sections.append({"id": len(sections), "offset": cursor, "bytes": size,
                         "type_raw_u16": kind, "raw_hex": section.hex(),
                         "image_ids": images})
        cursor += size
    if not sections:
        raise project.InputError("display payload contains no section")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "raw_hex": data.hex(), "prefix_hex": data[:46].hex(),
            "counter_attributes": attributes, "sections": sections}


def display_document(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    banks = [{"segment_id": i, "offset": s.offset,
              "slots": [slot for slot, _, _ in reader.walk_bank(s.data)]}
             for i, s in enumerate(game.segments) if s.ident == 10]

    def objects(data, global_list=False):
        result = []
        for obj in reader.object_definitions(data, globals_have_blocks=global_list):
            blocks = []
            if obj.object_type in SIGNATURES:
                for block_id, block in enumerate(obj.blocks):
                    if block.ident != 0:
                        continue
                    decoded = decode_display(block.data, obj.object_type)
                    for section in decoded["sections"]:
                        matches = []
                        for image in section["image_ids"] or []:
                            candidates = [bank["segment_id"] for bank in banks if image in bank["slots"]]
                            if not candidates:
                                raise project.InputError("display references an unoccupied image handle")
                            matches.append(candidates)
                        section["image_bank_candidates"] = matches if section["image_ids"] is not None else None
                    blocks.append({"block_id": block_id, "object_list_offset": block.offset,
                                   **decoded})
            result.append({"id": obj.index, "type": obj.object_type, "global": obj.is_global,
                           "deleted": obj.deleted, "display_data": blocks})
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
            "coverage": {"display_artwork_storage": True, "image_handles": True,
                         "runtime_display_semantics": False, "global_reference_resolution": False,
                         "other_object_images": False, "behaviour": False}}


def save_displays(document, repo=project.REPO):
    return project.save_export(document, json.dumps(
        document, ensure_ascii=True, indent=2, sort_keys=True) + "\n", "displays.json", repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            document = display_document(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        print(save_displays(document).relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Display exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
