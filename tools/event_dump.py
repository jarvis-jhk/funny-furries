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
from tools import integer_constants

VERSION = "event-dump/29"
EXPRESSION_TYPES = frozenset({15, 22, 23, 45, 52, 53})
POSITION_PARAMETER_BYTES = {9: 34, 16: 26, 18: 36, 21: 34}
SCALAR_WORD_TYPES = frozenset({3, 4, 5, 10, 12, 14, 15, 17, 26, 32, 34})
SCALAR_DWORD_TYPES = frozenset({2, 24, 29})
ADDRESS_HEADER_TYPES = frozenset({6, 7, 8, 9, 11, 13, 18, 19, 20, 21, 25,
                                  27, 28, 30, 31, 33, 35, 36, 37, 38, 39})
ADDRESS_PAYLOAD_TYPES = frozenset({40})


def word(data, offset, form="<H"):
    size = struct.calcsize(form)
    if offset + size > len(data):
        raise project.InputError("truncated event field")
    return struct.unpack_from(form, data, offset)[0]


def decode_expression(payload):
    """Expose stored tokens, without evaluating or guessing operator meanings."""
    prefix = word(payload, 0)
    cursor = 2
    tokens = []
    while True:
        code = word(payload, cursor)
        if code == 0:
            # The external reader stops here. Keep the rest opaque, including
            # observed padding, instead of interpreting it as more tokens.
            return {"prefix_raw_u16": prefix, "tokens": tokens,
                    "terminator_payload_offset": cursor,
                    "suffix_hex": payload[cursor + 2:].hex(),
                    "constant_integer_evaluation": integer_constants.evaluate(tokens)}
        size = word(payload, cursor + 2)
        if size < 4 or cursor + size > len(payload):
            raise project.InputError("expression token length exceeds its parameter")
        kind = code & 0xFF
        target = None
        if 0 < kind < 0x80:
            if size < 8:
                raise project.InputError("object expression token is shorter than its header")
            target = {"reference_raw_u16": word(payload, cursor + 4),
                      "expected_type": kind if code >= 0x3000 else None,
                      "status": "frame_context_unresolved", "candidates": []}
        tokens.append({"id": len(tokens), "payload_offset": cursor,
                       "bytes": size, "code_raw_u16": code,
                       "meaning": "unknown", "raw_hex": payload[cursor:cursor + size].hex(),
                       "object_reference_annotation": target})
        if code in (0xFFFF, 0xFEFF, 0xFDFF):
            # The original dispatcher recursively evaluates an operand for
            # FFFF; its evaluator leaves either stop word at the cursor.
            # This does not establish delimiter pairing or argument grammar.
            if size != 4:
                raise project.InputError("expression control token has an unsupported extent")
            if code == 0xFFFF:
                tokens[-1]["expression_control"] = {
                    "operation": "recursive_operand", "inner_start_token_offset": 4,
                    "inner_return_cursor": "unconsumed_evaluator_stop",
                    "dispatch_return_cursor": "after_stop_token",
                    "delimiter_pairing": "unknown", "other_operand_tags": "unknown",
                    "evidence": "cnc_runtime_dispatch"}
            else:
                tokens[-1]["expression_control"] = {
                    "operation": "evaluator_stop", "return_cursor": "unconsumed",
                    "delimiter_role": "unknown", "evidence": "cnc_runtime_evaluator"}
        if code == 0x0200:
            # The original evaluator's operator table selects an addition
            # handler. Only its numeric branch has independent execution proof;
            # a token alone never establishes the surrounding operand tags.
            if size != 4:
                raise project.InputError("addition operator token has an unsupported extent")
            tokens[-1]["integer_operation"] = {
                "name": "add", "bits": 32, "overflow": "wrap_modulo_2_32",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_operator_table"}
        if code == 0x0400:
            # The evaluator selects left-minus-right between operands; its
            # operand dispatcher consumes this same code as a prefix sign.
            # Storage alone cannot decide which context actually executes.
            if size != 4:
                raise project.InputError("minus token has an unsupported extent")
            tokens[-1]["integer_operation"] = {
                "name": "subtract", "operand_order": "left_minus_right",
                "bits": 32, "overflow": "wrap_modulo_2_32",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_operator_table"}
            tokens[-1]["integer_prefix_operation"] = {
                "name": "negate", "bits": 32, "overflow": "wrap_modulo_2_32",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_dispatch"}
        if code == 0x0600:
            # The original handler keeps the low 32 product bits and clears
            # the result tag. Proven numeric probes do not establish the
            # surrounding operands or certify nonnumeric input behavior.
            if size != 4:
                raise project.InputError("multiplication operator token has an unsupported extent")
            tokens[-1]["integer_operation"] = {
                "name": "multiply", "bits": 32, "overflow": "wrap_modulo_2_32",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_operator_table"}
        if code == 0x0800:
            # Numeric IDIV truncates toward zero, with a separate zero-divisor
            # return path. INT32_MIN / -1 faults instead of wrapping; the
            # original process's exception recovery remains unverified.
            if size != 4:
                raise project.InputError("division operator token has an unsupported extent")
            tokens[-1]["integer_operation"] = {
                "name": "divide", "operand_order": "left_divided_by_right",
                "bits": 32, "signed": True, "rounding": "toward_zero",
                "zero_divisor_result": 0, "overflow": "x86_divide_error",
                "exception_recovery": "unknown",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_operator_table"}
        if code == 0x0A00:
            # IDIV supplies a signed remainder; the zero-divisor branch keeps
            # the dividend. INT32_MIN % -1 still faults in the original CPU,
            # even though its mathematical remainder would be zero.
            if size != 4:
                raise project.InputError("remainder operator token has an unsupported extent")
            tokens[-1]["integer_operation"] = {
                "name": "remainder", "operand_order": "left_remainder_right",
                "bits": 32, "signed": True, "quotient_rounding": "toward_zero",
                "nonzero_result_sign": "dividend", "zero_divisor_result": "left_operand",
                "overflow": "x86_divide_error", "exception_recovery": "unknown",
                "required_operand_tag": 0, "other_operand_tags": "unknown",
                "evidence": "cnc_runtime_operator_table"}
        if code == 0x00FF:
            # The original CnC dispatcher selects the numeric handler which
            # loads token+4 into EAX. Do not borrow the newer SDK's wider code.
            if size != 8:
                raise project.InputError("integer literal token has an unsupported extent")
            tokens[-1]["integer_literal"] = {
                "token_offset": 4, "value_signed_i32": word(payload, cursor + 4, "<i"),
                "value_raw_u32": word(payload, cursor + 4, "<I"),
                "evidence": "cnc_runtime_dispatch"}
        if code == 0x03FF:
            # The original handler returns token+4 with a string tag. Retain
            # byte values: the executable does not establish their codepage.
            field = payload[cursor + 4:cursor + size]
            terminator = field.find(b"\0")
            if terminator < 0:
                raise project.InputError("string literal token has no bounded terminator")
            value = field[:terminator]
            tokens[-1]["string_literal"] = {
                "token_offset": 4, "bytes_hex": value.hex(),
                "byte_view_latin1": value.decode("latin1"),
                "terminator_token_offset": 4 + terminator,
                "suffix_hex": field[terminator + 1:].hex(),
                "source_encoding": "unknown", "evidence": "cnc_runtime_dispatch"}
        cursor += size


def decode_position_references(payload, kind):
    """Expose reference words; coordinate inputs have a separate annotation."""
    if len(payload) + 4 < POSITION_PARAMETER_BYTES[kind]:
        raise project.InputError("object-position parameter is shorter than its supported layout")
    references = []
    fields = [("position_reference", 0)]
    if kind in (9, 18):
        fields.append(("creation_target", 24))
    for role, offset in fields:
        reference = word(payload, offset)
        absolute = role == "position_reference" and reference in (0xFFFE, 0xFFFF)
        references.append({"role": role, "payload_offset": offset,
                           "reference_raw_u16": reference,
                           "status": "absolute_position_sentinel" if absolute else "frame_context_unresolved",
                           "candidates": []})
    return {"references": references}


def decode_position_coordinates(payload, kind):
    """Retain helper coordinate inputs, without selecting runtime objects."""
    if len(payload) + 4 < POSITION_PARAMETER_BYTES[kind]:
        raise project.InputError("object-position parameter is shorter than its supported layout")
    reference, flags = word(payload, 0), word(payload, 2)
    # The negative-reference helper branch loads these words directly. Positive
    # references need selection, and flag bit 0 bypasses the cartesian words.
    # Source slot encodings do not prove which runtime branch will be reached.
    usage = ("absolute_xy" if reference in (0xFFFE, 0xFFFF) else
             "context_dependent")
    return {"flags_payload_offset": 2, "flags_raw_u16": flags,
            "x": {"payload_offset": 4, "raw_u16": word(payload, 4),
                  "signed_i16": word(payload, 4, "<h")},
            "y": {"payload_offset": 6, "raw_u16": word(payload, 6),
                  "signed_i16": word(payload, 6, "<h")},
            "word_usage": usage, "runtime_resolution": False,
            "evidence": "cnc_position_helper_coordinate_inputs"}


def decode_object_parameter(payload):
    # The pinned independent registry identifies only the slot at parameter+6.
    # Adjacent words do not establish an expected type or qualifier semantics.
    if len(payload) < 6:
        raise project.InputError("object parameter is shorter than its supported layout")
    return {"payload_offset": 2, "reference_raw_u16": word(payload, 2),
            "status": "frame_context_unresolved", "candidates": []}


def decode_address_getter(payload, kind):
    # Exact dispatch entries return the parameter address unchanged, or +4 for
    # type40. Nothing here proves what the eventual caller reads through it.
    if kind not in ADDRESS_HEADER_TYPES | ADDRESS_PAYLOAD_TYPES:
        raise project.InputError("parameter type has no supported address getter")
    offset = 0 if kind in ADDRESS_HEADER_TYPES else 4
    return {"conditional_getter_return": {
                "assumption": "execution_reaches_original_parameter_getter_dispatch",
                "eax": "runtime_parameter_address_unknown",
                "parameter_relative_offset": offset,
                "address_arithmetic_bits": 32,
                "address_overflow": "wrap_modulo_2_to_32",
                "target": "parameter_header" if offset == 0 else "parameter_payload",
                "bx_raw_u16": 0, "carry": False,
                "dx": "preserved_incoming_word_not_a_new_value_tag"},
            "stored_bytes_from_target": len(payload) + 4 - offset,
            "payload_dereferenced_by_getter": False,
            "caller_interpretation": "unknown", "runtime_resolution": False,
            "evidence": "cnc_parameter_address_getters"}


def decode_object_getter(payload):
    # The runtime helper reads the first payload WORD; the editor reference
    # candidate is a different word. Neither determines live selector state.
    decode_object_parameter(payload)
    return {"selection_input_payload_offset": 0,
            "selection_input_raw_u16": word(payload, 0),
            "runtime_gate_byte": "unknown",
            "conditional_inactive_return": {
                "assumption": "type1_dispatch_and_runtime_gate_byte_zero",
                "eax": "runtime_parameter_header_address_unknown",
                "parameter_relative_offset": 0, "bx_raw_u16": 0,
                "carry": False, "dx": "preserved_incoming_word_not_a_new_value_tag",
                "payload_dereferenced_by_getter": False},
            "conditional_active_normal_return": {
                "assumption": "type1_dispatch_nonzero_gate_and_selection_helper_normal_return",
                "eax": "selection_helper_return_esi",
                "helper_carry_set": {"bx_raw_u16": 0, "carry": False},
                "helper_carry_clear": {"bx": "selection_helper_return_bx", "carry": True},
                "dx": "selection_helper_return_word_not_a_new_expression_tag",
                "returned_pointer_validity": "unknown",
                "selection_helper_side_effects": "live_state_dependent"},
            "selected_branch": "requires_live_runtime_gate",
            "resolved_eax": None, "caller_interpretation": "unknown",
            "runtime_resolution": False,
            "evidence": "cnc_type1_state_dependent_parameter_getter"}


def decode_scalar_getter(payload, kind):
    # These exact original dispatch entries directly load parameter+4. EAX
    # transport does not establish the caller's signedness, units or purpose.
    if kind not in SCALAR_WORD_TYPES | SCALAR_DWORD_TYPES:
        raise project.InputError("parameter type has no supported scalar getter")
    bits = 16 if kind in SCALAR_WORD_TYPES else 32
    value = word(payload, 0, "<H" if bits == 16 else "<I")
    return {"payload_offset": 0, "stored_bits": bits, "stored_raw_unsigned": value,
            "opaque_suffix_hex": payload[bits // 8:].hex(),
            "conditional_getter_return": {
                "assumption": "execution_reaches_original_parameter_getter_dispatch",
                "eax_raw_u32": value, "extension": "zero_extend" if bits == 16 else "none",
                "bx_raw_u16": 0, "carry": False,
                "dx": "preserved_incoming_word_not_a_new_value_tag"},
            "caller_interpretation": "unknown", "runtime_resolution": False,
            "evidence": "cnc_immediate_scalar_parameter_getters"}


def decode_fixed_value_getter(payload):
    # Type42 loads a DWORD and a separate WORD eight bytes later. INC BX
    # wraps without masking; no caller units or comparison meaning is proven.
    value = word(payload, 0, "<I")
    control = word(payload, 8)
    return {"value_payload_offset": 0, "value_raw_u32": value,
            "control_payload_offset": 8, "control_raw_u16": control,
            "opaque_middle_hex": payload[4:8].hex(),
            "opaque_suffix_hex": payload[10:].hex(),
            "conditional_getter_return": {
                "assumption": "execution_reaches_original_type42_parameter_getter",
                "eax_raw_u32": value, "bx_raw_u16": (control + 1) & 0xFFFF,
                "carry": False,
                "dx": "preserved_incoming_word_not_a_new_value_tag"},
            "caller_interpretation": "unknown", "runtime_resolution": False,
            "evidence": "cnc_type42_fixed_value_parameter_getter"}


def decode_position_getter(payload):
    # Type16 calls the position helper with BX0, then packs its returned words.
    # The final SUB clears carry even when the helper returned failure; no
    # live object coordinates or failure-path values can be inferred here.
    coordinates = decode_position_coordinates(payload, 16)
    reference = word(payload, 0)
    probe = {"status": "requires_live_object_state"}
    if reference & 0x8000:
        probe = {"status": "value",
                 "eax_raw_u32": (coordinates["x"]["raw_u16"] << 16) |
                                coordinates["y"]["raw_u16"],
                 "dx_raw_u16": 0, "bx_raw_u16": 0, "carry": False}
    return {"helper_input_payload_offset": 0, "helper_input_bx_raw_u16": 0,
            "reference_raw_u16": reference,
            "conditional_normal_return": {
                "assumption": "type16_dispatch_and_position_helper_normal_return",
                "eax_high_word": "helper_return_x_raw_u16",
                "eax_low_word": "helper_return_y_raw_u16",
                "dx": "helper_return_word_not_a_new_expression_tag",
                "bx_raw_u16": 0, "carry": False,
                "helper_carry_preserved": False,
                "helper_failure_coordinate_values": "unknown"},
            "conditional_absolute_return": probe,
            "absolute_branch_test": "reference_word_sign_bit_set",
            "caller_interpretation": "unknown", "runtime_resolution": False,
            "evidence": "cnc_type16_position_parameter_getter"}


def decode_expression_getter(expression):
    # Only type22's exact dispatch entry is proven here. Reader expression
    # layouts for other types do not imply this runtime getter evaluates them.
    result = expression["constant_integer_evaluation"]
    probe = {"status": result["status"]}
    if result["status"] == "value":
        probe.update({"eax_raw_u32": result["value_raw_u32"],
                      "dx_raw_u16": 0, "bx_raw_u16": 0, "carry": False})
    elif result["status"] == "cpu_exception":
        probe.update({"fault": result["fault"], "vector": result["vector"],
                      "exception_recovery": "unknown"})
    return {"first_token_parameter_offset": 6, "first_token_payload_offset": 2,
            "stored_prefix_read_by_getter": False,
            "conditional_normal_return": {
                "assumption": "type22_dispatch_and_expression_normal_return",
                "eax": "expression_evaluator_result",
                "dx": "expression_evaluator_tag_not_preserved_incoming_word",
                "bx_raw_u16": 0, "carry": False},
            "conditional_closed_integer_return": probe,
            "caller_interpretation": "unknown", "runtime_resolution": False,
            "evidence": "cnc_type22_expression_parameter_getter"}


def decode_type45_getter(expression):
    # Exact type45 dispatch shares the expression wrapper, but caller content
    # remains unknown. Only a lone byte-string token gets an address contract.
    out = decode_expression_getter(expression)
    out["conditional_normal_return"]["assumption"] = "type45_dispatch_and_expression_normal_return"
    out["evidence"] = "cnc_type45_expression_parameter_getter"
    out["conditional_lone_string_return"] = {"status": "unsupported_shape"}
    tokens = expression["tokens"]
    if len(tokens) == 1 and tokens[0]["code_raw_u16"] == 0x03FF:
        literal = tokens[0]["string_literal"]
        out["conditional_lone_string_return"] = {
            "status": "parameter_byte_string_address",
            "eax": "runtime_parameter_address_unknown",
            "parameter_relative_offset": 4 + tokens[0]["payload_offset"] + literal["token_offset"],
            "address_arithmetic_bits": 32, "address_overflow": "wrap_modulo_2_to_32",
            "bytes_hex": literal["bytes_hex"], "dx_raw_u16": 1,
            "bx_raw_u16": 0, "carry": False, "source_encoding": "unknown"}
    return out


def decode_comparison_prefix(payload):
    # Type23's getter transports the prefix separately from the expression.
    # Numeric consumers mask it before signed comparison; that path is an
    # explicit assumption, never a result for the containing event condition.
    raw = word(payload, 0)
    index = raw & 0x7FFF
    operations = ("equal", "not_equal", "less_or_equal", "less",
                  "greater_or_equal", "greater")
    return {"payload_offset": 0, "raw_u16": raw,
            "getter_bx_on_normal_expression_return_raw_u16": (raw + 1) & 0xFFFF,
            "getter_carry_on_normal_expression_return": False,
            "conditional_integer_consumer": {
                "assumption": "execution_reaches_original_signed_integer_comparison_path",
                "index_mask_raw_u16": 0x7FFF, "index_raw_u16": index,
                "opaque_high_bit_raw_u16": raw & 0x8000,
                "status": "table_entry" if index < len(operations) else "outside_proven_table",
                "operation": operations[index] if index < len(operations) else None,
                "operand_order": "caller_left_vs_expression_right",
                "operand_bits": 32, "signed": True,
                "left_value": None, "condition_result": None},
            "runtime_resolution": False,
            "evidence": "cnc_type23_getter_and_signed_comparison_paths"}



def decode_group_parameter(payload):
    # The independent converter clears this u32 in actions. Its runtime address
    # is not a source-program offset. The following word is only an equality key.
    if len(payload) < 4:
        raise project.InputError("event-group parameter has no complete runtime word")
    return {"runtime_raw_u32": word(payload, 0, "<I"),
            "key_raw_u16": word(payload, 4) if len(payload) >= 6 else None,
            "suffix_hex": payload[6 if len(payload) >= 6 else 4:].hex(),
            "status": "program_context_unresolved", "candidates": []}


def annotate_group_parameters(document):
    globals_ = document["global_events"]

    def candidates(program, scope):
        result = []
        for row in program["rows"]:
            annotation = row["event_group_annotation"]
            title = annotation["title"]
            if annotation["kind"] == "open" and title is not None:
                result.append({**scope, "row_id": row["id"], "row_offset": row["offset"],
                               "matching_row_id": annotation["matching_row_id"],
                               "key_raw_u16": title["prefix_raw_u16"][1], "title": title})
        return result

    global_candidates = [c for p in globals_ for c in candidates(p, {"scope": "global", "segment_id": p["segment_id"]})]
    for frame in document["frames"]:
        for program in frame["programs"]:
            available = candidates(program, {"scope": "frame", "frame_id": frame["id"],
                                             "block_id": program["block_id"]}) + global_candidates
            annotate_group_program(program, available)
    for program in globals_:
        annotate_group_program(program, global_candidates)
    return document


def annotate_group_program(program, available):
    # Expose ALL byte-equality candidates. Do not pick a scope, infer activation
    # or discard unclosed groups: those choices need runtime/editor evidence.
    for row in program["rows"]:
        for record in row["records"]:
            for parameter in record["parameters"]:
                target = parameter.get("group_parameter_storage")
                if target is None:
                    continue
                key = target["key_raw_u16"]
                target["candidates"] = [c for c in available if key is not None and c["key_raw_u16"] == key]
                count = len(target["candidates"])
                target["status"] = ("no_key_word" if key is None else "no_stored_word_match" if not count
                                    else "stored_word_candidate" if count == 1 else "ambiguous_stored_word")


def decode_frame_target(payload):
    if len(payload) < 2:
        raise project.InputError("frame-target action parameter has no complete target word")
    return {"payload_offset": 0, "target_raw_u16": word(payload, 0),
            "probe_method": "raw_target_as_level_number_table_index",
            "status": "table_context_unresolved", "candidates": [],
            "runtime_resolution": "unknown"}


def level_number_storage(game):
    # The CnC reader names this segment but does not interpret its fields.
    # Word views and index probes preserve evidence without inventing frame IDs.
    tables = []
    for segment_id, segment in enumerate(game.segments):
        if segment.ident != 7:
            continue
        data = segment.data
        tables.append({"segment_id": segment_id, "offset": segment.offset,
                       "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "raw_hex": data.hex(), "meaning": "unknown",
                       "words": [{"id": i // 2, "payload_offset": i,
                                  "raw_u16": word(data, i)}
                                 for i in range(0, len(data) - 1, 2)],
                       "suffix_hex": data[len(data) // 2 * 2:].hex()})
    return tables


def annotate_frame_targets(program, tables):
    for row in program["rows"]:
        for record in row["records"]:
            for parameter in record["parameters"]:
                target = parameter.get("frame_target_storage")
                if target is None:
                    continue
                index = target["target_raw_u16"]
                candidates = [{"segment_id": table["segment_id"], "slot_id": index,
                               "payload_offset": table["words"][index]["payload_offset"],
                               "raw_u16": table["words"][index]["raw_u16"]}
                              for table in tables if index < len(table["words"])]
                target["candidates"] = candidates
                target["status"] = ("table_slot_unavailable" if not candidates else
                                    "table_slot_probe" if len(candidates) == 1 else
                                    "ambiguous_table_slot_probes")
    return program


def decode_audio_reference(payload, kind):
    if len(payload) < 2:
        raise project.InputError("audio parameter has no complete bank handle")
    return {"kind": "sound" if kind == 6 else "music", "payload_offset": 0,
            "reference_raw_u16": word(payload, 0),
            "status": "bank_context_unresolved", "candidates": []}


def audio_banks(reader, game):
    banks = []
    for segment_id, segment in enumerate(game.segments):
        kind = reader.BANK_SEGMENTS.get(segment.ident)
        if kind not in ("sound", "music"):
            continue
        entries = {slot: {"segment_id": segment_id, "id": slot, "kind": kind,
                          "offset": offset, "bytes": size,
                          "record_sha256": hashlib.sha256(segment.data[offset:offset + size]).hexdigest()}
                   for slot, offset, size in reader.walk_bank(segment.data)}
        banks.append((kind, entries))
    return banks


def annotate_audio(program, banks):
    # Application banks are shared by frame and global programs. A duplicate
    # bank is evidence of ambiguity, never a reason to choose its first entry.
    for row in program["rows"]:
        for record in row["records"]:
            for parameter in record["parameters"]:
                target = parameter.get("audio_reference_storage")
                if target is None:
                    continue
                candidates = [entries[target["reference_raw_u16"]]
                              for kind, entries in banks
                              if kind == target["kind"] and target["reference_raw_u16"] in entries]
                target["candidates"] = candidates
                target["status"] = ("missing_bank_slot" if not candidates else
                                    "bank_slot_candidate" if len(candidates) == 1 else "ambiguous_bank_slot")
    return program


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
        if code in ADDRESS_HEADER_TYPES | ADDRESS_PAYLOAD_TYPES:
            parameters[-1]["address_getter_storage"] = decode_address_getter(
                data[cursor + 4:cursor + size], code)
        if code in SCALAR_WORD_TYPES | SCALAR_DWORD_TYPES:
            parameters[-1]["scalar_getter_storage"] = decode_scalar_getter(
                data[cursor + 4:cursor + size], code)
        if code == 26 and role == "action":
            parameters[-1]["frame_target_storage"] = decode_frame_target(data[cursor + 4:cursor + size])
        if code == 42:
            parameters[-1]["fixed_value_getter_storage"] = decode_fixed_value_getter(
                data[cursor + 4:cursor + size])
        if code == 39:
            parameters[-1]["group_parameter_storage"] = decode_group_parameter(data[cursor + 4:cursor + size])
        if code == 1:
            parameters[-1]["object_parameter_reference"] = decode_object_parameter(data[cursor + 4:cursor + size])
            parameters[-1]["object_getter_storage"] = decode_object_getter(data[cursor + 4:cursor + size])
        if code in EXPRESSION_TYPES:
            parameters[-1]["expression_storage"] = decode_expression(data[cursor + 4:cursor + size])
        if code == 22:
            parameters[-1]["expression_getter_storage"] = decode_expression_getter(
                parameters[-1]["expression_storage"])
        if code == 45:
            parameters[-1]["type45_getter_storage"] = decode_type45_getter(
                parameters[-1]["expression_storage"])
        if code == 23:
            parameters[-1]["comparison_prefix_storage"] = decode_comparison_prefix(
                data[cursor + 4:cursor + size])
        if code in POSITION_PARAMETER_BYTES:
            parameters[-1]["position_reference_storage"] = decode_position_references(
                data[cursor + 4:cursor + size], code)
            parameters[-1]["position_coordinate_storage"] = decode_position_coordinates(
                data[cursor + 4:cursor + size], code)
        if code == 16:
            parameters[-1]["position_getter_storage"] = decode_position_getter(
                data[cursor + 4:cursor + size])
        if code in (6, 7):
            parameters[-1]["audio_reference_storage"] = decode_audio_reference(data[cursor + 4:cursor + size], code)
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
            return annotate_groups(rows)
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


def annotate_groups(rows):
    """Keep editor group nesting separate from unknown execution semantics."""
    stack = []
    for row in rows:
        first = row["records"][0] if row["condition_count"] else None
        marker = first["opcode"] if first and first["object_type"] == -1 else None
        kind = "open" if marker == -10 else "close" if marker == -11 else "event"
        annotation = {"kind": kind, "enclosing_open_row_ids": list(stack),
                      "matching_row_id": None, "title": None}
        if kind == "open":
            parameters = [p for p in first["parameters"] if p["type"] == 38]
            # Only the observed ANSI 80-byte field is interpreted. Other valid
            # parameter shapes remain lossless raw data, not guessed titles.
            if len(parameters) == 1 and parameters[0]["bytes"] == 88:
                payload = bytes.fromhex(parameters[0]["payload_hex"])
                field = payload[4:84]
                name = field.split(b"\0", 1)[0]
                annotation["title"] = {
                    "parameter_id": parameters[0]["id"],
                    "prefix_raw_u16": list(struct.unpack_from("<HH", payload)),
                    "field_hex": field.hex(), "bytes_hex": name.hex(),
                    "byte_view_latin1": name.decode("latin1"),
                    "source_encoding": "unknown"}
            stack.append(row["id"])
        elif kind == "close" and stack:
            opened = stack.pop()
            annotation["enclosing_open_row_ids"] = list(stack)
            annotation["matching_row_id"] = opened
            rows[opened]["event_group_annotation"]["matching_row_id"] = row["id"]
        row["event_group_annotation"] = annotation
    return rows


def group_structure(rows):
    opens = [r["id"] for r in rows if r["event_group_annotation"]["kind"] == "open"]
    unclosed = [i for i in opens if rows[i]["event_group_annotation"]["matching_row_id"] is None]
    unmatched = [r["id"] for r in rows if r["event_group_annotation"]["kind"] == "close"
                 and r["event_group_annotation"]["matching_row_id"] is None]
    return {"status": "unbalanced" if unclosed or unmatched else "balanced",
            "open_row_ids": opens, "unclosed_open_row_ids": unclosed,
            "unmatched_close_row_ids": unmatched}


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
    rows = decode_rows(data[10:end])
    return {"header_hex": data[:6].hex(), "program_offset": 10,
            "program_bytes": size, "rows": rows, "event_groups": group_structure(rows),
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
    rows = decode_rows(data[start:start + size])
    return {"header_hex": data[:header_size].hex(), "program_offset": start,
            "program_bytes": size, "rows": rows, "event_groups": group_structure(rows),
            "auxiliary": [{"id": 0, "offset": header_size,
                           "bytes": start - header_size, "meaning": "unknown",
                           "raw_hex": data[header_size:start].hex()}]}


def reference_annotation(record, object_lists):
    """Match storage slots only; encoded references need separate evidence."""
    reference = record["object_reference"]
    kind = record["object_type"]
    unsigned = reference & 0xFFFF
    result = {"reference_raw_u16": unsigned, "status": "non_object_type",
              "candidates": []}
    # System records also carry a word at +4; treating that as an object slot
    # would attach unrelated object names to keyboard/timer/etc. operations.
    # Common object-expression tokens supply no proven expected type (None).
    # Their unique live slot is a candidate, without inventing a type match.
    if kind is not None and kind <= 0:
        return result
    if unsigned >= 0x4000:
        result["status"] = "encoded_reference_unresolved"
        return result
    for block_id, objects in object_lists:
        for obj in objects:
            if obj["id"] == reference:
                result["candidates"].append({"block_id": block_id,
                    **{key: obj[key] for key in
                       ("id", "name", "type", "type_name", "global", "deleted")}})
    candidates = result["candidates"]
    if not candidates:
        result["status"] = "missing_local_slot"
    elif len(candidates) > 1:
        result["status"] = "ambiguous_local_slot"
    elif candidates[0]["deleted"]:
        result["status"] = "deleted_local_slot"
    elif kind is not None and candidates[0]["type"] != kind:
        result["status"] = "type_mismatch"
    else:
        result["status"] = "local_slot_candidate" if kind is None else "local_slot_match"
    return result


def event_document(reader, raw):
    # Reuse strict container, object-table and bank validation before any output.
    inventory = project.inventory(reader, raw)
    game = reader.read(raw)
    banks = audio_banks(reader, game)
    number_tables = level_number_storage(game)
    frames = []
    for frame, level in enumerate(game.levels()):
        programs = []
        frame_index = inventory["frames"][frame]
        list_ids = [i for i, block in enumerate(frame_index["blocks"]) if block["id"] == 2]
        object_lists = list(zip(list_ids, frame_index["object_lists"]))
        for block_id, block in enumerate(reader.level_blocks(level.data)[1]):
            if block.ident == 4:
                program = annotate_frame_targets(annotate_audio(decode_program(block.data), banks), number_tables)
                for row in program["rows"]:
                    for record in row["records"]:
                        record["object_reference_annotation"] = reference_annotation(record, object_lists)
                        for parameter in record["parameters"]:
                            target = parameter.get("object_parameter_reference")
                            if target is not None:
                                target.update(reference_annotation({
                                    "object_type": None,
                                    "object_reference": target["reference_raw_u16"]}, object_lists))
                            for target in parameter.get("position_reference_storage", {}).get("references", []):
                                if target["status"] != "absolute_position_sentinel":
                                    target.update(reference_annotation({
                                        "object_type": None,
                                        "object_reference": target["reference_raw_u16"]}, object_lists))
                            for token in parameter.get("expression_storage", {}).get("tokens", []):
                                target = token["object_reference_annotation"]
                                if target is not None:
                                    target.update(reference_annotation({
                                        "object_type": target["expected_type"],
                                        "object_reference": target["reference_raw_u16"]}, object_lists))
                programs.append({"block_id": block_id, "frame_offset": block.offset,
                                 "bytes": len(block.data), **program})
        frames.append({"id": frame, "programs": programs})
    return annotate_group_parameters({"schema_version": 29, "exporter": VERSION,
            "source": inventory["source"], "reader_sha256": inventory["reader_sha256"],
            "coverage": {"frame_event_structure": True, "opcode_semantics": False,
                         "parameter_semantics": False, "global_event_structure": True,
                         "frame_local_reference_candidates": True,
                         "editor_group_structure": True,
                         "expression_token_storage": True,
                         "expression_integer_literals": True,
                         "expression_string_literals": True,
                         "expression_integer_addition": True,
                         "expression_integer_minus": True,
                         "expression_integer_multiplication": True,
                         "expression_integer_division": True,
                         "expression_integer_remainder": True,
                         "expression_control_tokens": True,
                         "constant_integer_expressions": True,
                         "recursive_integer_constants": True,
                         "comparison_prefix_inputs": True,
                         "immediate_scalar_getter_inputs": True,
                         "parameter_address_getter_inputs": True,
                         "type22_expression_getter_inputs": True,
                         "type16_position_getter_inputs": True,
                         "type1_object_getter_inputs": True,
                         "type42_fixed_value_getter_inputs": True,
                         "type45_expression_getter_inputs": True,
                         "expression_evaluation": False,
                         "position_reference_storage": True,
                         "position_coordinate_storage": True,
                         "position_resolution": False,
                         "audio_bank_reference_candidates": True,
                         "object_parameter_reference_candidates": True,
                         "group_parameter_stored_word_candidates": True,
                         "frame_target_storage": True,
                         "level_number_word_probes": True,
                         "frame_target_resolution": False,
                         "global_reference_resolution": False},
            "frames": frames, "level_number_storage": number_tables,
            "global_events": [{"segment_id": slot, "offset": segment.offset,
                               "bytes": len(segment.data), "meaning": "unknown",
                               "sha256": hashlib.sha256(segment.data).hexdigest(),
                               "raw_hex": segment.data.hex(),
                               **annotate_frame_targets(annotate_audio(decode_global_program(segment.data), banks), number_tables)}
                              for slot, segment in enumerate(game.segments) if segment.ident == 3]})


def readable_program(program):
    lines = []
    for row in program["rows"]:
        lines.append(f"    ROW {row['id']} offset={row['offset']} bytes={row['bytes']} "
                     f"conditions={row['condition_count']} actions={row['action_count']} "
                     f"header={row['header_hex']}")
        group = row["event_group_annotation"]
        lines.append("      GROUP " + json.dumps(group, ensure_ascii=True, sort_keys=True))
        for record in row["records"]:
            lines.append(f"      {record['role'].upper()} {record['id']} "
                         f"offset={record['offset']} bytes={record['bytes']} "
                         f"type={record['object_type']} opcode={record['opcode']} "
                         f"reference={record['object_reference']} meaning=UNKNOWN "
                         f"header={record['header_hex']}")
            if "object_reference_annotation" in record:
                annotation = record["object_reference_annotation"]
                # JSON quoting keeps arbitrary original names on one text line.
                names = json.dumps(annotation["candidates"], ensure_ascii=True, sort_keys=True)
                lines.append(f"        REFERENCE status={annotation['status']} candidates={names}")
            for parameter in record["parameters"]:
                lines.append(f"        PARAM {parameter['id']} offset={parameter['offset']} "
                             f"bytes={parameter['bytes']} type={parameter['type']} "
                             f"meaning=UNKNOWN payload={parameter['payload_hex']}")
                if "frame_target_storage" in parameter:
                    lines.append("          FRAME_TARGET " + json.dumps(
                        parameter["frame_target_storage"], ensure_ascii=True, sort_keys=True))
                if "group_parameter_storage" in parameter:
                    lines.append("          GROUP_PARAMETER " + json.dumps(
                        parameter["group_parameter_storage"], ensure_ascii=True, sort_keys=True))
                if "object_parameter_reference" in parameter:
                    lines.append("          OBJECT_PARAMETER_REFERENCE " + json.dumps(
                        parameter["object_parameter_reference"], ensure_ascii=True, sort_keys=True))
                if "object_getter_storage" in parameter:
                    lines.append("          OBJECT_GETTER " + json.dumps(
                        parameter["object_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "expression_storage" in parameter:
                    lines.append("          EXPRESSION " + json.dumps(
                        parameter["expression_storage"], ensure_ascii=True, sort_keys=True))
                if "comparison_prefix_storage" in parameter:
                    lines.append("          COMPARISON_PREFIX " + json.dumps(
                        parameter["comparison_prefix_storage"], ensure_ascii=True, sort_keys=True))
                if "expression_getter_storage" in parameter:
                    lines.append("          EXPRESSION_GETTER " + json.dumps(
                        parameter["expression_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "type45_getter_storage" in parameter:
                    lines.append("          TYPE45_GETTER " + json.dumps(
                        parameter["type45_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "position_getter_storage" in parameter:
                    lines.append("          POSITION_GETTER " + json.dumps(
                        parameter["position_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "address_getter_storage" in parameter:
                    lines.append("          ADDRESS_GETTER " + json.dumps(
                        parameter["address_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "scalar_getter_storage" in parameter:
                    lines.append("          SCALAR_GETTER " + json.dumps(
                        parameter["scalar_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "fixed_value_getter_storage" in parameter:
                    lines.append("          FIXED_VALUE_GETTER " + json.dumps(
                        parameter["fixed_value_getter_storage"], ensure_ascii=True, sort_keys=True))
                if "position_reference_storage" in parameter:
                    lines.append("          POSITION_REFERENCES " + json.dumps(
                        parameter["position_reference_storage"], ensure_ascii=True, sort_keys=True))
                if "position_coordinate_storage" in parameter:
                    lines.append("          POSITION_COORDINATES " + json.dumps(
                        parameter["position_coordinate_storage"], ensure_ascii=True, sort_keys=True))
                if "audio_reference_storage" in parameter:
                    lines.append("          AUDIO_REFERENCE " + json.dumps(
                        parameter["audio_reference_storage"], ensure_ascii=True, sort_keys=True))
    lines.append("    TERMINATOR 0000")
    lines.append("    GROUP_STRUCTURE " + json.dumps(program["event_groups"], sort_keys=True))
    for auxiliary in program["auxiliary"]:
        lines.append(f"    AUX {auxiliary['id']} offset={auxiliary['offset']} "
                     f"bytes={auxiliary['bytes']} meaning=UNKNOWN raw={auxiliary['raw_hex']}")
    return lines


def readable(document):
    lines = [f"Funny Furries {VERSION}", f"Source SHA-256: {document['source']['sha256']}",
             "Opcode/parameter execution UNKNOWN; integer/string literals, numeric addition/minus/multiplication/division/remainder and expression control tokens decoded; closed ungrouped/recursive integer constants evaluated.",
             "Row/record/parameter offsets are relative to the event program."]
    for table in document.get("level_number_storage", []):
        lines.append("LEVEL_NUMBER_STORAGE " + json.dumps(table, ensure_ascii=True, sort_keys=True))
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
