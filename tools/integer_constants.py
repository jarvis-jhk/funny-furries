"""Evaluate only closed, ungrouped numeric token streams proven in the CnC runtime."""
from __future__ import annotations

LITERAL = 0x00FF
MINUS = 0x0400
OPERATORS = frozenset({0x0200, MINUS, 0x0600, 0x0800, 0x0A00})


def signed32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def evaluate(tokens):
    # Refuse the whole stream before arithmetic: a dynamic tail must not turn
    # an earlier apparent divide error into a claim about the actual expression.
    unsupported = [t["id"] for t in tokens if t["code_raw_u16"] not in OPERATORS | {LITERAL}]
    if unsupported:
        return {"status": "unsupported_tokens", "token_ids": unsupported}
    operands, operations = [], []
    cursor = 0
    while cursor < len(tokens):
        negate = tokens[cursor]["code_raw_u16"] == MINUS
        cursor += int(negate)
        if cursor == len(tokens) or tokens[cursor]["code_raw_u16"] != LITERAL:
            return {"status": "unsupported_shape"}
        value = tokens[cursor]["integer_literal"]["value_signed_i32"]
        operands.append(signed32(-value) if negate else value)
        cursor += 1
        if cursor == len(tokens):
            break
        operation = tokens[cursor]
        if operation["code_raw_u16"] not in OPERATORS:
            return {"status": "unsupported_shape"}
        operations.append(operation)
        cursor += 1
    if not operands or len(operands) != len(operations) + 1:
        return {"status": "unsupported_shape"}

    values, pending = [operands[0]], []

    def reduce():
        operation = pending.pop()
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
        return None

    for operation, operand in zip(operations, operands[1:]):
        # The original compares the raw signed16 operator words, rather than
        # grouping multiply/divide/remainder into a conventional equal priority.
        while pending and pending[-1]["code_raw_u16"] >= operation["code_raw_u16"]:
            fault = reduce()
            if fault is not None:
                return fault
        pending.append(operation)
        values.append(operand)
    while pending:
        fault = reduce()
        if fault is not None:
            return fault
    return {"status": "value", "value_signed_i32": values[0],
            "value_raw_u32": values[0] & 0xFFFFFFFF, "result_tag": 0,
            "evidence": "cnc_runtime_evaluator"}
