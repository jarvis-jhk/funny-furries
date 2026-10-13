"""Evaluate only closed numeric token streams proven in the CnC runtime."""
from __future__ import annotations

LITERAL = 0x00FF
MINUS = 0x0400
OPERATORS = frozenset({0x0200, MINUS, 0x0600, 0x0800, 0x0A00})
RECURSIVE = 0xFFFF
STOPS = frozenset({0xFEFF, 0xFDFF})


def signed32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def evaluate(tokens):
    # Refuse the whole stream before arithmetic: a dynamic tail must not turn
    # an earlier apparent divide error into a claim about the actual expression.
    unsupported = [t["id"] for t in tokens
                   if t["code_raw_u16"] not in OPERATORS | STOPS | {LITERAL, RECURSIVE}]
    if unsupported:
        return {"status": "unsupported_tokens", "token_ids": unsupported}
    # Build the complete execution order before doing any arithmetic. Each
    # frame is one evaluator invocation; a stop returns its value to the
    # operand dispatcher, which consumes that stop and applies the prefix sign.
    # Explicit frames avoid depending on Python's recursion limit for input.
    instructions = []
    frames = [{"pending": [], "negate": False}]
    cursor = 0
    want_operand = True
    while cursor < len(tokens):
        if want_operand:
            negate = tokens[cursor]["code_raw_u16"] == MINUS
            cursor += int(negate)
            if cursor == len(tokens):
                return {"status": "unsupported_shape"}
            operand = tokens[cursor]
            cursor += 1
            if operand["code_raw_u16"] == RECURSIVE:
                frames.append({"pending": [], "negate": negate})
                continue
            if operand["code_raw_u16"] != LITERAL:
                return {"status": "unsupported_shape"}
            instructions.append(("literal", operand))
            if negate:
                instructions.append(("negate", None))
            want_operand = False
            continue
        operation = tokens[cursor]
        code = operation["code_raw_u16"]
        pending = frames[-1]["pending"]
        if code in STOPS:
            if len(frames) == 1:
                return {"status": "unsupported_shape"}
            while pending:
                instructions.append(("binary", pending.pop()))
            frame = frames.pop()
            if frame["negate"]:
                instructions.append(("negate", None))
        elif code in OPERATORS:
            # Raw signed16 priorities are distinct in this positive-code
            # subset. Reduce before reading the next operand, as the original
            # does: a later recursive operand may itself raise a divide error.
            while pending and pending[-1]["code_raw_u16"] >= code:
                instructions.append(("binary", pending.pop()))
            pending.append(operation)
            want_operand = True
        else:
            return {"status": "unsupported_shape"}
        cursor += 1
    if want_operand or len(frames) != 1:
        return {"status": "unsupported_shape"}
    while frames[0]["pending"]:
        instructions.append(("binary", frames[0]["pending"].pop()))

    values = []
    for kind, operation in instructions:
        if kind == "literal":
            values.append(operation["integer_literal"]["value_signed_i32"])
            continue
        if kind == "negate":
            values[-1] = signed32(-values[-1])
            continue
        right, left = values.pop(), values.pop()
        code = operation["code_raw_u16"]
        if code == 0x0200:
            value = left + right
        elif code == MINUS:
            value = left - right
        elif code == 0x0600:
            value = left * right
        elif right == 0:
            value = 0 if code == 0x0800 else left
        elif left == -0x80000000 and right == -1:
            return {"status": "cpu_exception", "fault": "x86_divide_error", "vector": 0,
                    "operator_token_id": operation["id"], "exception_recovery": "unknown",
                    "evidence": "cnc_runtime_evaluator"}
        else:
            quotient = abs(left) // abs(right)
            if (left < 0) != (right < 0):
                quotient = -quotient
            value = quotient if code == 0x0800 else left - quotient * right
        values.append(signed32(value))
    return {"status": "value", "value_signed_i32": values[0],
            "value_raw_u32": values[0] & 0xFFFFFFFF, "result_tag": 0,
            "evidence": "cnc_runtime_evaluator"}
