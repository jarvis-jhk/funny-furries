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
from tools import frame_layout

VERSION = "backdrop-dump/9"
HEADER_BYTES = 68


def image_dimension_candidate(data, segment_id, slot, offset):
    # Decode only the stored metadata. PNG decoding and runtime bank selection
    # have their own contracts; neither follows from a matching image handle.
    if len(data) < 24:
        raise project.InputError("backdrop image has no complete metadata header")
    if struct.unpack_from("<I", data, 6)[0] != len(data) - 24:
        raise project.InputError("backdrop image length disagrees with its bank record")
    return {"segment_id": segment_id, "image_id": slot, "bank_offset": offset,
            "record_bytes": len(data), "header_hex": data[:24].hex(),
            "record_sha256": hashlib.sha256(data).hexdigest(),
            **{axis: {"image_record_offset": at,
                      "raw_u16": struct.unpack_from("<H", data, at)[0]}
               for axis, at in (("width", 10), ("height", 12))}}


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
    # The original refresh helper writes these inputs in this order. This is
    # conditional on the supplied header being selected, not runtime resolution
    # of the local/global body or an interpretation of opaque type bits.
    spans = [(50, 12, 4, None), (42, 6, 2, 0x0FFF)]
    if head[42] == 0:
        spans += [(24, 16, 4, None), (28, 20, 4, None),
                  (32, 24, 2, None), (34, 26, 2, None), (36, 28, 2, None)]
    spans.append((54, 8, 2, None))
    writes = []
    for source, target, size, mask in spans:
        value = int.from_bytes(head[source:source + size], "little")
        writes.append({"header_offset": source, "placement_offset": target,
                       "bytes": size, "raw_unsigned": value, "and_mask": mask,
                       "written_unsigned": value if mask is None else value & mask})
    refresh = {"meaning": "backdrop_placement_refresh_inputs",
               "evidence": "original_runtime_complete_header_refresh_helper",
               "runtime_resolution": False, "dispatch_low_byte": head[42],
               "writes": writes}
    return {"header_bytes": len(head), "header_sha256": hashlib.sha256(head).hexdigest(),
            "header_hex": head.hex(), "image_word_raw_u16": image, "artwork": artwork,
            "quick_backdrop_dimension_inputs": dimensions,
            "placement_refresh_inputs": refresh}


def backdrop_document(reader, raw):
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    banks, candidates, records = [], {}, {}
    for segment_id, segment in enumerate(game.segments):
        if segment.ident != 10:
            continue
        entries = list(reader.walk_bank(segment.data))
        banks.append({"segment_id": segment_id, "offset": segment.offset,
                      "slots": [slot for slot, _, _ in entries]})
        for slot, offset, size in entries:
            candidates.setdefault(slot, []).append(segment_id)
            records[segment_id, slot] = (segment.data[offset:offset + size], offset)
    dimensions = {}

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
                decoded["ordinary_backdrop_image_candidates"] = None
                if obj.object_type == 1:
                    entries = []
                    for segment_id in matches:
                        key = (segment_id, image)
                        if key not in dimensions:
                            record_data, offset = records[key]
                            dimensions[key] = image_dimension_candidate(record_data, segment_id, image, offset)
                        entries.append(dimensions[key])
                    decoded["ordinary_backdrop_image_candidates"] = {
                        "meaning": "ordinary_backdrop_image_dimension_candidates",
                        "evidence": "stored_image_metadata",
                        "runtime_resolution": False,
                        "status": "single_bank_candidate" if len(entries) == 1 else "multiple_bank_candidates",
                        "candidates": entries}
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
    for level, frame in zip(game.levels(), frames):
        frame["placement_refresh_probes"] = placement_refresh_probes(
            reader.level_blocks(level.data)[1], frame["object_lists"])
    return {"schema_version": 9, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "image_banks": banks, "global_object_lists": globals_, "frames": frames,
            "coverage": {"backdrop_header_artwork": True, "image_handles": True,
                         "quick_backdrop_dimension_inputs": True,
                         "ordinary_backdrop_image_dimension_candidates": True,
                         "backdrop_placement_refresh_inputs": True,
                         "local_placement_refresh_probes": True,
                         "conditional_quick_rectangle_inputs": True,
                         "conditional_quick_fill_inputs": True,
                         "conditional_ordinary_rectangle_inputs": True,
                         "conditional_image_metadata_call_inputs": True,
                         "runtime_rendering": False, "global_reference_resolution": False,
                         "arena_geometry": False, "spawns": False, "behaviour": False}}


def placement_refresh_probes(blocks, object_lists):
    # The first word is only an equality probe. Keep every same-frame header,
    # even a conflicting type, and never pick a global body or a winning list.
    definitions = {}
    for objects in object_lists:
        for obj in objects["objects"]:
            definitions.setdefault(obj["id"], []).append((objects["block_id"], obj))
    result = []
    for block_id, block in enumerate(blocks):
        if block.ident != 3:
            continue
        stored = frame_layout.decode_placements(block.data)
        records = []
        for record in stored["records"]:
            raw = bytes.fromhex(record["raw_hex"])
            word = int.from_bytes(raw[:2], "little")
            candidates = []
            for definition_block, obj in definitions.get(word, []):
                preview = None
                rectangle = None
                fill = None
                ordinary_rectangle = None
                metadata_call = None
                decoded = obj["backdrop"]
                if decoded is not None and not obj["deleted"]:
                    preview = bytearray(raw)
                    for write in decoded["placement_refresh_inputs"]["writes"]:
                        at, size = write["placement_offset"], write["bytes"]
                        preview[at:at + size] = write["written_unsigned"].to_bytes(size, "little")
                    if obj["type"] == 0:
                        rectangle = quick_rectangle_inputs(preview)
                        fill = quick_fill_inputs(preview)
                    else:
                        ordinary_rectangle = ordinary_rectangle_inputs(
                            preview, decoded["ordinary_backdrop_image_candidates"])
                    metadata_call = image_metadata_call_inputs(preview, obj["type"])
                    preview = preview.hex()
                candidates.append({"definition_block_id": definition_block,
                    **{key: obj[key] for key in
                       ("id", "type", "global", "deleted", "object_list_offset")},
                    "status": "deleted_definition" if obj["deleted"] else
                              "conditional_backdrop_refresh" if decoded is not None else
                              "non_backdrop_definition",
                    "header_sha256": decoded["header_sha256"] if decoded is not None else None,
                    "conditional_record_hex": preview,
                    "conditional_quick_rectangle_inputs": rectangle,
                    "conditional_quick_fill_inputs": fill,
                    "conditional_ordinary_rectangle_inputs": ordinary_rectangle,
                    "conditional_image_metadata_call_inputs": metadata_call})
            records.append({"id": record["id"], "offset": record["offset"],
                "raw_hex": record["raw_hex"], "object_word_raw_u16": word,
                "status": "missing_local_slot" if not candidates else
                          "single_local_candidate" if len(candidates) == 1 else
                          "multiple_local_candidates",
                "runtime_resolution": False,
                "evidence": "stored_word_local_slot_equality_and_conditional_header_refresh",
                "candidates": candidates})
        result.append({"block_id": block_id, "frame_offset": block.offset,
                       "placement_sha256": stored["sha256"],
                       "slots": stored["slots"], "records": records})
    return result


def quick_rectangle_inputs(record):
    if len(record) != frame_layout.RECORD_BYTES:
        raise project.InputError("quick rectangle requires a complete placement record")
    # Drawing subtracts two signed runtime words from the stored coordinates.
    # Their live values and header selection are unavailable in a project file;
    # expose the rule and a clearly conditional zero-translation calculation.
    fields = {name: {"record_offset": at,
                     "raw_u16": struct.unpack_from("<H", record, at)[0],
                     "signed_i16": struct.unpack_from("<h", record, at)[0]}
              for name, at in (("x", 2), ("y", 4), ("width", 26), ("height", 28))}
    x, y, width, height = (fields[name]["signed_i16"] for name in
                           ("x", "y", "width", "height"))
    return {"meaning": "conditional_quick_rectangle_inputs",
            "evidence": "original_runtime_origin_subtraction_and_quick_rectangle_paths",
            "runtime_resolution": False, "fields": fields,
            "translation_inputs": {
                axis: {"runtime_word_address": address, "signed_i16": None}
                for axis, address in (("x", "0x41d662"), ("y", "0x41d664"))},
            "origin_rule": "signed_record_coordinate - signed_runtime_translation",
            "exclusive_endpoint_rule": "origin + signed_refreshed_dimension",
            "zero_translation_edges": {"left": x, "top": y,
                                       "right_exclusive": x + width,
                                       "bottom_exclusive": y + height}}


def quick_fill_inputs(record):
    if len(record) != frame_layout.RECORD_BYTES:
        raise project.InputError("quick fill requires a complete placement record")
    fill = struct.unpack_from("<H", record, 24)[0]
    kind = fill & 15
    if kind not in (0, 1, 2):
        raise project.InputError("unsupported quick fill dispatch nibble")
    image = struct.unpack_from("<H", record, 8)[0]
    colors = [struct.unpack_from("<I", record, at)[0] for at in (16, 20)]
    # The original fill path consumes the full refreshed word: its high-byte
    # bit 0 swaps gradient arguments, independently of editor orientation.
    # Stop at call inputs; neither import behavior nor live clipping is known.
    branch = "gradient" if kind == 2 else "mosaic_metadata_required" if kind == 1 and image else "solid"
    gradient = None
    if kind == 2:
        swapped = bool(fill & 0x0100)
        gradient = {"swap_colors": swapped, "swap_mask": 0x0100,
                    "first_color_raw_u32": colors[1 if swapped else 0],
                    "second_color_raw_u32": colors[0 if swapped else 1],
                    "flags_mask": 0x00F0, "flags_raw_u16": fill & 0x00F0,
                    "flags_high_u16_input": None,
                    "flags_argument_rule": "(incoming_edx & 0xFFFF0000) | (refreshed_fill_word & 0x00F0)"}
    return {"meaning": "conditional_quick_fill_call_inputs",
            "evidence": "original_runtime_fill_dispatch_and_call_argument_paths",
            "runtime_resolution": False,
            "fill_word": {"record_offset": 24, "raw_u16": fill, "dispatch_nibble": kind},
            "image_word": {"record_offset": 8, "raw_u16": image},
            "colors": [{"record_offset": at, "raw_u32": value}
                       for at, value in zip((16, 20), colors)],
            "branch": branch, "mosaic_zero_image_solid_fallback": kind == 1 and image == 0,
            "solid_color_raw_u32": colors[0] if branch == "solid" else None,
            "gradient_arguments": gradient,
            "clipping_inputs": {name: {"signed_i32": None}
                                for name in ("origin_x", "origin_y", "right_clip", "bottom_clip")},
            "inclusive_endpoint_rule": "signed_min(origin + signed_refreshed_dimension - 1, clip)",
            "arithmetic": "x86_32bit_wrap_before_signed_min",
            "drawing_performed": False}


def ordinary_rectangle_inputs(record, images):
    if len(record) != frame_layout.RECORD_BYTES:
        raise project.InputError("ordinary rectangle requires a complete placement record")
    # The original post-lookup path sign-extends returned metadata words. Stored
    # image words are hypothetical inputs only: neither the lookup nor equality
    # between its result and this bank record has been established.
    coordinates = {axis: {"record_offset": at,
                          "raw_u16": struct.unpack_from("<H", record, at)[0],
                          "signed_i16": struct.unpack_from("<h", record, at)[0]}
                   for axis, at in (("x", 2), ("y", 4))}
    x, y = (coordinates[axis]["signed_i16"] for axis in ("x", "y"))
    candidates = []
    for image in images["candidates"]:
        fields = {axis: {**image[axis],
                         "signed_i16": struct.unpack("<h", image[axis]["raw_u16"].to_bytes(2, "little"))[0]}
                  for axis in ("width", "height")}
        candidates.append({**{key: image[key] for key in
                              ("segment_id", "image_id", "bank_offset", "record_sha256")},
                           "fields": fields,
                           "zero_translation_candidate_edges": {
                               "left": x, "top": y,
                               "right_exclusive": x + fields["width"]["signed_i16"],
                               "bottom_exclusive": y + fields["height"]["signed_i16"]}})
    return {"meaning": "conditional_ordinary_rectangle_inputs",
            "evidence": "original_runtime_origin_and_post_metadata_rectangle_paths",
            "runtime_resolution": False, "metadata_lookup_performed": False,
            "coordinates": coordinates,
            "image_word": {"record_offset": 8,
                           "raw_u16": struct.unpack_from("<H", record, 8)[0]},
            "translation_inputs": {
                axis: {"runtime_word_address": address, "signed_i16": None}
                for axis, address in (("x", "0x41d662"), ("y", "0x41d664"))},
            "metadata_result_inputs": {
                axis: {"returned_buffer_offset": at, "signed_i16": None}
                for axis, at in (("width", 10), ("height", 12))},
            "origin_rule": "signed_record_coordinate - signed_runtime_translation",
            "exclusive_endpoint_rule": "origin + signed_returned_metadata_dimension",
            "candidate_assumption": "returned_dimension_words_equal_this_stored_image_candidate",
            "status": images["status"], "dimension_candidates": candidates}


def image_metadata_call_inputs(record, kind):
    if len(record) != frame_layout.RECORD_BYTES:
        raise project.InputError("image metadata call requires a complete placement record")
    image = struct.unpack_from("<H", record, 8)[0]
    if kind == 0:
        fill = struct.unpack_from("<H", record, 24)[0] & 15
        if fill not in (0, 1, 2):
            raise project.InputError("unsupported quick fill dispatch nibble")
        if fill != 1 or image == 0:
            return None
        path = "quick_mosaic"
        argument = {"low_u16": image, "high_u16": 0, "raw_u32": image,
                    "rule": "zero_extended_image_word"}
        call = "0x405528"
    elif kind == 1:
        # The ordinary caller stores only AX at stack+18, then reads a dword.
        # Its upper half overlaps the LOW word of the translated left edge at
        # stack+20; it is not the neighbouring placement word or a cleared half.
        x = struct.unpack_from("<h", record, 2)[0]
        path = "ordinary"
        argument = {"low_u16": image, "high_u16": None, "raw_u32": None,
                    "rule": "((translated_origin_x & 0xFFFF) << 16) | image_word",
                    "origin_x_input": {
                        "record_offset": 2, "raw_u16": struct.unpack_from("<H", record, 2)[0],
                        "signed_i16": x, "runtime_translation_word_address": "0x41d662",
                        "runtime_translation_signed_i16": None,
                        "rule": "signed_record_x - signed_runtime_translation_x"},
                    "zero_translation_argument_raw_u32": ((x & 0xFFFF) << 16) | image}
        call = "0x4058a9"
    else:
        return None
    return {"meaning": "conditional_image_metadata_call_inputs",
            "evidence": "original_runtime_metadata_call_argument_paths",
            "path": path, "call_instruction_address": call,
            "callee_thunk_address": "0x414186", "runtime_resolution": False,
            "metadata_lookup_performed": False, "drawing_performed": False,
            "image_word": {"record_offset": 8, "raw_u16": image},
            "arguments_in_stack_order": ["runtime_context", "image_argument", "output_buffer"],
            "runtime_context_input": {"runtime_dword_address": "0x41d4e4", "raw_u32": None},
            "image_argument": argument,
            "output_buffer_input": {"storage": "caller_stack", "runtime_address": None},
            "callee_argument_interpretation": "unresolved"}


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
