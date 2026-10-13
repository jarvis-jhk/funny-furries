#!/usr/bin/env python3
"""Export ordered CnC event records; unknown semantics remain explicit."""
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

VERSION = "event-dump/2"


def word(data, offset, form="<H"):
    size = struct.calcsize(form)
    if offset + size > len(data):
        raise project.InputError("truncated event field")
    return struct.unpack_from(form, data, offset)[0]


def decode_record(data, role, offset, index):
    header_size = 14 if role == "condition" else 12
    if len(data) < header_size:
        raise project.InputError("event record is shorter than its header")
    parameters = []
    cursor = header_size
    for number in range(data[10]):
        size = word(data, cursor)
        code = word(data, cursor + 2)
        if size < 4 or cursor + size > len(data):
            raise project.InputError("event parameter length exceeds its record")
        parameters.append({"id": number, "offset": offset + cursor, "bytes": size,
                           "type": code, "meaning": "unknown",
                           "payload_hex": data[cursor + 4:cursor + size].hex()})
        cursor += size
    if cursor != len(data):
        raise project.InputError("event parameter count leaves trailing record bytes")
    return {"id": index, "role": role, "offset": offset, "bytes": len(data),
            "object_type": word(data, 2, "<b"), "opcode": word(data, 3, "<b"),
            "object_reference": word(data, 4, "<h"), "meaning": "unknown",
            "header_hex": data[:header_size].hex(), "parameters": parameters}


def decode_rows(data):
    rows = []
    cursor = 0
    while True:
        signed_size = word(data, cursor, "<h")
        if signed_size == 0:
            if cursor + 2 != len(data):
                raise project.InputError("event row terminator has trailing bytes")
            return rows
        size = abs(signed_size)
        if size < 14 or cursor + size > len(data):
            raise project.InputError("event row length exceeds its program")
        row = data[cursor:cursor + size]
        conditions, actions = row[2], row[3]
        records = []
        position = 14
        for number in range(conditions + actions):
            record_size = word(row, position)
            role = "condition" if number < conditions else "action"
            if record_size < (14 if role == "condition" else 12) or position + record_size > size:
                raise project.InputError("event record length exceeds its row")
            records.append(decode_record(row[position:position + record_size], role,
                                         cursor + position, number))
            position += record_size
        if position != size:
            raise project.InputError("event record count leaves trailing row bytes")
        rows.append({"id": len(rows), "offset": cursor, "bytes": size,
                     "signed_size": signed_size, "header_hex": row[:14].hex(),
                     "condition_count": conditions, "action_count": actions,
                     "records": records})
        cursor += size


def decode_program(data):
    # Headerless runtime programs and other event dialects need separate proof.
    if data[:4] != b"Fra\0" or word(data, 4) != 0x0217:
        raise project.InputError("expected an unprotected Fra event header v0217")
    size = word(data, 6, "<I")
    end = 10 + size
    if end > len(data):
        raise project.InputError("event program length exceeds its block")
    second_size = word(data, end)
    third = end + 2 + second_size
    if third > len(data):
        raise project.InputError("event auxiliary block length exceeds its block")
    return {"header_hex": data[:6].hex(), "program_offset": 10,
            "program_bytes": size, "rows": decode_rows(data[10:end]),
            "auxiliary": [{"id": 2, "offset": end + 2, "bytes": second_size,
                           "meaning": "unknown", "raw_hex": data[end + 2:third].hex()},
                          {"id": 3, "offset": third, "bytes": len(data) - third,
                           "meaning": "unknown", "raw_hex": data[third:].hex()}]}


def decode_global_program(data):
    # This CnC container has no Fra signature. Only the observed 40-byte
    # header dialect is supported; the intervening editor region stays opaque.
    if len(data) < 40:
        raise project.InputError("global event header is truncated")
    total = word(data, 0, "<I")
    header_size = word(data, 8, "<I")
    start = word(data, 12, "<I")
    size = word(data, 16, "<I")
    if total != len(data) or header_size != 40:
        raise project.InputError("unsupported global event header extent")
    if start < header_size or size < 2 or start + size != total:
        raise project.InputError("global event program extent is invalid")
    return {"header_hex": data[:header_size].hex(), "program_offset": start,
            "program_bytes": size, "rows": decode_rows(data[start:start + size]),
            "auxiliary": [{"id": 0, "offset": header_size,
                           "bytes": start - header_size, "meaning": "unknown",
                           "raw_hex": data[header_size:start].hex()}]}


def event_document(reader, raw):
    # Reuse strict container, object-table and bank validation before any output.
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    frames = []
    for frame, level in enumerate(game.levels()):
        programs = []
        for block_id, block in enumerate(reader.level_blocks(level.data)[1]):
            if block.ident == 4:
                programs.append({"block_id": block_id, "frame_offset": block.offset,
                                 "bytes": len(block.data), **decode_program(block.data)})
        frames.append({"id": frame, "programs": programs})
    return {"schema_version": 2, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "coverage": {"frame_event_structure": True, "opcode_semantics": False,
                         "parameter_semantics": False, "global_event_structure": True},
            "frames": frames,
            "global_events": [{"segment_id": slot, "offset": segment.offset,
                               "bytes": len(segment.data), "meaning": "unknown",
                               "sha256": hashlib.sha256(segment.data).hexdigest(),
                               "raw_hex": segment.data.hex(),
                               **decode_global_program(segment.data)}
                              for slot, segment in enumerate(game.segments) if segment.ident == 3]}


def readable_program(program):
    lines = []
    for row in program["rows"]:
        lines.append(f"    ROW {row['id']} offset={row['offset']} bytes={row['bytes']} "
                     f"conditions={row['condition_count']} actions={row['action_count']} "
                     f"header={row['header_hex']}")
        for record in row["records"]:
            lines.append(f"      {record['role'].upper()} {record['id']} "
                         f"offset={record['offset']} bytes={record['bytes']} "
                         f"type={record['object_type']} opcode={record['opcode']} "
                         f"reference={record['object_reference']} meaning=UNKNOWN "
                         f"header={record['header_hex']}")
            for parameter in record["parameters"]:
                lines.append(f"        PARAM {parameter['id']} offset={parameter['offset']} "
                             f"bytes={parameter['bytes']} type={parameter['type']} "
                             f"meaning=UNKNOWN payload={parameter['payload_hex']}")
    lines.append("    TERMINATOR 0000")
    for auxiliary in program["auxiliary"]:
        lines.append(f"    AUX {auxiliary['id']} offset={auxiliary['offset']} "
                     f"bytes={auxiliary['bytes']} meaning=UNKNOWN raw={auxiliary['raw_hex']}")
    return lines


def readable(document):
    lines = [f"Funny Furries {VERSION}", f"Source SHA-256: {document['source']['sha256']}",
             "All opcode/parameter meanings UNKNOWN; this is structure, not behaviour.",
             "Row/record/parameter offsets are relative to the event program."]
    for frame in document["frames"]:
        lines.append(f"FRAME {frame['id']} ({len(frame['programs'])} event blocks)")
        for program in frame["programs"]:
            lines.append(f"  BLOCK {program['block_id']} frame_offset={program['frame_offset']} "
                         f"program_offset={program['program_offset']} header={program['header_hex']}")
            lines.extend(readable_program(program))
    for segment in document["global_events"]:
        lines.append(f"GLOBAL SEGMENT {segment['segment_id']} offset={segment['offset']} "
                     f"bytes={segment['bytes']} program_offset={segment['program_offset']} "
                     f"program_bytes={segment['program_bytes']} header={segment['header_hex']}")
        lines.extend(readable_program(segment))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    parser.add_argument("--text", action="store_true", help="write events.txt instead of events.json")
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            document = event_document(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        payload = readable(document) if args.text else json.dumps(
            document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        target = project.save_export(document, payload, "events.txt" if args.text else "events.json")
        print(target.relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Event exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
