#!/usr/bin/env python3
"""Export lossless CnC frame headers and placement storage, without guessed geometry."""
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

VERSION = "frame-layout/4"
UNUSED = 0xFFFFFFFF
RECORD_BYTES = 32


def decode_placements(data):
    if len(data) < 2:
        raise project.InputError("placement block has no complete slot count")
    count = struct.unpack_from("<H", data)[0]
    base = 2 + 4 * count
    if base > len(data):
        raise project.InputError("placement pointer table is truncated")
    pointers = struct.unpack_from(f"<{count}I", data, 2)
    records = data[base:]
    if len(records) % RECORD_BYTES:
        raise project.InputError("unsupported placement record size or trailing bytes")
    used = set()
    slots = []
    for slot, pointer in enumerate(pointers):
        entry = {"id": slot, "pointer_raw_u32": pointer, "record_id": None}
        if pointer != UNUSED:
            if pointer % RECORD_BYTES or pointer + RECORD_BYTES > len(records):
                raise project.InputError("placement pointer is unaligned or out of bounds")
            entry["record_id"] = pointer // RECORD_BYTES
            used.add(entry["record_id"])
        slots.append(entry)
    # Unreachable bytes are not silently dropped or invented as live instances.
    if len(used) != len(records) // RECORD_BYTES:
        raise project.InputError("placement storage has unreferenced records")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "records_offset": base, "record_bytes": RECORD_BYTES,
            "slots": slots,
            "records": [{"id": index, "offset": base + index * RECORD_BYTES,
                         "meaning": "unknown",
                         "raw_hex": records[index * RECORD_BYTES:(index + 1) * RECORD_BYTES].hex()}
                        for index in range(len(records) // RECORD_BYTES)]}


def layout_document(reader, raw):
    inventory = project.inventory(reader, raw)
    frames = []
    for frame_id, level in enumerate(reader.read(raw).levels()):
        start, blocks = reader.level_blocks(level.data)
        placements = [{"block_id": block_id, "frame_offset": block.offset,
                       **decode_placements(block.data)}
                      for block_id, block in enumerate(blocks) if block.ident == 3]
        lists = iter(inventory["frames"][frame_id]["object_lists"])
        annotate_object_slot_probes(placements, [(block_id, next(lists))
            for block_id, block in enumerate(blocks) if block.ident == 2])
        annotate_coordinate_inputs(placements)
        annotate_creation_types(placements)
        frames.append({"id": frame_id, "offset": level.offset,
                       "header_bytes": start, "header_meaning": "unknown",
                       "header_hex": level.data[:start].hex(), "placements": placements})
    return {"schema_version": 4, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "frames": frames,
            "coverage": {"frame_headers": True, "placement_storage": True,
                         "placement_object_slot_probes": True,
                         "placement_coordinate_inputs": True,
                         "placement_creation_type_inputs": True,
                         "placement_semantics": False, "arena_geometry": False,
                         "spawns": False, "behaviour": False}}


def annotate_creation_types(placements):
    # The creator masks record6 to its low byte before dispatching allocation.
    # Header equality does not prove body selection or successful creation.
    for block in placements:
        for record in block["records"]:
            word = struct.unpack_from("<H", bytes.fromhex(record["raw_hex"]), 6)[0]
            kind = word & 0xFF
            record["creation_type_input"] = {
                "record_offset": 6, "raw_u16": word,
                "type_raw_u8": kind, "opaque_high_u8": word >> 8,
                "meaning": "creation_type_input",
                "evidence": "original_runtime_creation_type_dispatch",
                "runtime_resolution": False,
                "local_definition_comparisons": [{
                    **{key: obj[key] for key in ("block_id", "id", "type", "deleted")},
                    "type_equal": obj["type"] == kind}
                    for obj in record["object_slot_probe"]["candidates"]]}


def annotate_coordinate_inputs(placements):
    # The original creator copies these words only when its corresponding
    # override is 0x8000. They are inputs, not proven final positions/spawns.
    for block in placements:
        for record in block["records"]:
            raw = bytes.fromhex(record["raw_hex"])
            axes = {}
            for axis, offset in (("x", 2), ("y", 4)):
                axes[axis] = {"record_offset": offset,
                    "raw_u16": struct.unpack_from("<H", raw, offset)[0],
                    "signed_i16": struct.unpack_from("<h", raw, offset)[0]}
            record["coordinate_inputs"] = {**axes,
                "meaning": "creation_coordinate_inputs",
                "evidence": "original_runtime_creation_coordinate_branch",
                "use_record_when_override_raw_u16": 0x8000,
                "runtime_resolution": False}


def annotate_object_slot_probes(placements, object_lists):
    # Equality with a local slot is research evidence, not a decoded runtime
    # reference. Do not import event encodings/sentinels or choose a global body.
    slots = {}
    for block_id, objects in object_lists:
        for obj in objects:
            slots.setdefault(obj["id"], []).append({"block_id": block_id,
                **{key: obj[key] for key in
                   ("id", "name", "type", "type_name", "flags", "global", "deleted")}})
    for block in placements:
        for record in block["records"]:
            value = struct.unpack_from("<H", bytes.fromhex(record["raw_hex"]))[0]
            candidates = slots.get(value, [])
            status = ("missing_local_slot" if not candidates else
                      "ambiguous_local_slot" if len(candidates) > 1 else
                      "deleted_local_slot" if candidates[0]["deleted"] else
                      "local_slot_probe")
            record["object_slot_probe"] = {
                "record_offset": 0, "word_raw_u16": value, "status": status,
                "candidates": candidates, "runtime_resolution": False,
                "evidence": "stored_word_local_slot_equality"}


def save_layout(document, repo=project.REPO):
    return project.save_export(document, json.dumps(
        document, ensure_ascii=True, indent=2, sort_keys=True) + "\n", "frame-layout.json", repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            document = layout_document(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        print(save_layout(document).relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Frame layout exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
