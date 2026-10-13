import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


def number(value):
    return token(0xFF, struct.pack('<i', value))


def result(items):
    return events.decode_expression(expression(items))['constant_integer_evaluation']


class IntegerConstantTests(unittest.TestCase):
    def test_signed_literals_and_single_prefix_negation_wrap(self):
        for value in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
            for prefix in ([], [token(0x400)]):
                out = result(prefix + [number(value)])
                expected = (-value if prefix else value) & 0xFFFFFFFF
                self.assertEqual(out, {'status': 'value', 'value_signed_i32': expected - 2**32 if expected >= 2**31 else expected,
                                       'value_raw_u32': expected, 'result_tag': 0,
                                       'evidence': 'cnc_runtime_evaluator'})

    def test_raw_operator_priority_and_equal_code_left_associativity(self):
        cases = [([number(20), token(0x600), number(7), token(0x800), number(3)], 40),
                 ([number(20), token(0x800), number(7), token(0xA00), number(3)], 20),
                 ([number(20), token(0x800), number(3), token(0x800), number(2)], 3),
                 ([number(20), token(0x400), number(7), token(0x400), number(3)], 10),
                 ([number(7), token(0x200), number(3), token(0x600), number(5)], 22),
                 ([number(2), token(0x600), token(0x400), number(3), token(0x200), number(7)], 1)]
        for items, expected in cases:
            with self.subTest(items=items):
                self.assertEqual(result(items)['value_signed_i32'], expected)

    def test_intermediate_wrap_signed_rounding_zero_divisors_and_remainder(self):
        cases = [([number(2147483647), token(0x200), number(1)], -2147483648),
                 ([number(-2147483648), token(0x400), number(1)], 2147483647),
                 ([number(65536), token(0x600), number(65536)], 0),
                 ([number(-7), token(0x800), number(3)], -2),
                 ([number(7), token(0x800), number(-3)], -2),
                 ([number(-7), token(0xA00), number(3)], -1),
                 ([number(7), token(0xA00), number(-3)], 1),
                 ([number(-2147483648), token(0x800), number(0)], 0),
                 ([number(-2147483648), token(0xA00), number(0)], -2147483648),
                 ([number(2147483647), token(0x200), number(1), token(0x200), number(1), token(0x800), number(2)], -2147483648)]
        for items, expected in cases:
            with self.subTest(items=items):
                self.assertEqual(result(items)['value_signed_i32'], expected)

    def test_cpu_overflow_identifies_pending_operator_without_invented_result(self):
        for code in (0x800, 0xA00):
            items = [number(7), token(0x200), number(-2147483648), token(code), number(-1)]
            self.assertEqual(result(items), {'status': 'cpu_exception', 'fault': 'x86_divide_error', 'vector': 0,
                                            'operator_token_id': 3, 'exception_recovery': 'unknown',
                                            'evidence': 'cnc_runtime_evaluator'})
            # A same-priority divide reduces first, while a higher-priority
            # remainder changes the right operand before the divide can fault.
        self.assertEqual(result([number(-2147483648), token(0x800), number(-1), token(0xA00), number(-1)])['value_signed_i32'], 0)
        self.assertEqual(result([number(-2147483648), token(0x800), number(-1), token(0x800), number(-1)])['operator_token_id'], 1)

    def test_full_stream_refusal_precedes_arithmetic_and_preserves_unknowns(self):
        unsupported = [token(0x3FF, b'x\0'),
                       token(0x0C00), token(0x0A02, struct.pack('<HH', 7, 9))]
        for tail in unsupported:
            items = [number(-2147483648), token(0x800), number(-1), token(0x200), tail]
            raw = expression(items)
            out = events.decode_expression(raw)
            self.assertEqual(out['constant_integer_evaluation'], {'status': 'unsupported_tokens', 'token_ids': [4]})
            self.assertEqual(reconstruct_expression(out), raw)
            self.assertTrue(all(t['meaning'] == 'unknown' for t in out['tokens']))
        for items in ([], [token(0x400)], [token(0x400), token(0x400), number(1)],
                      [number(1), number(2)], [token(0x200), number(1)],
                      [number(1), token(0x600)],
                      [number(-2147483648), token(0x800), number(-1), token(0x200)]):
            with self.subTest(items=items):
                self.assertEqual(result(items), {'status': 'unsupported_shape'})

    def test_prefix_and_suffix_stay_opaque_and_long_stream_is_bounded_by_tokens(self):
        raw = expression([number(17)], prefix=0xBEEF, suffix=number(123) + b'opaque')
        out = events.decode_expression(raw)
        self.assertEqual(out['constant_integer_evaluation']['value_signed_i32'], 17)
        self.assertEqual(out['prefix_raw_u16'], 0xBEEF)
        self.assertEqual(out['suffix_hex'], (number(123) + b'opaque').hex())
        self.assertEqual(reconstruct_expression(out), raw)
        items = [number(1)] + [t for _ in range(4096) for t in (token(0x200), number(1))]
        self.assertEqual(result(items)['value_signed_i32'], 4097)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class IntegerConstantContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_expression_types_both_roles_scopes_readable_and_lossless(self):
        payload = expression([number(20), token(0x600), number(7), token(0x800), number(3)])
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, program = expression_project(payload)
            old_word = struct.pack('<HH', len(payload) + 4, 22)
            new_word = struct.pack('<HH', len(payload) + 4, kind)
            raw = raw.replace(old_word, new_word)
            program = program.replace(old_word, new_word)
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['constant_integer_expressions'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            for prog in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                self.assertEqual(reconstruct_program(prog), program)
                for rec in prog['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['type'], kind)
                    self.assertEqual(q['expression_storage']['constant_integer_evaluation']['value_signed_i32'], 40)
            self.assertEqual(events.readable(doc).count('"value_signed_i32": 40'), 10)
            self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_unknown_and_trap_are_research_output_without_fault_reporting(self):
        for items, status in [([number(-2147483648), token(0x800), number(-1)], 'cpu_exception'),
                              ([number(1), token(0x200), token(0xFFFF)], 'unsupported_shape')]:
            raw, _ = expression_project(expression(items))
            with patch.object(project, 'report_fault') as report:
                doc = events.event_document(self.reader, raw)
                manifest, files = export_project.research_bundle(self.reader, raw)
                self.assertEqual(files['events.json'], export_project.json_bytes(doc))
                self.assertEqual(files['events.txt'], events.readable(doc).encode())
                self.assertIn(('"status": "' + status + '"').encode(), files['events.txt'])
                report.assert_not_called()
                scratch_root = project.REPO / 'build'
                scratch_root.mkdir(exist_ok=True)
                with tempfile.TemporaryDirectory(dir=scratch_root) as scratch:
                    target = export_project.save_bundle(manifest, files, Path(scratch))
                    first = {p.name: p.read_bytes() for p in target.iterdir()}
                    export_project.save_bundle(*export_project.research_bundle(self.reader, raw), Path(scratch))
                    self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, first)

    def test_late_invalid_literal_refuses_json_text_bundle_and_fault_reporting(self):
        raw, _ = expression_project(expression([number(20), token(0x800), number(3)]))
        at = raw.rfind(number(3))
        raw = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in [(events, []), (events, ['--text']), (export_project, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(export_project, 'save_bundle') as bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); bundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_source_streams_independent_eligible_words_and_unknowns(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        game = self.reader.read(raw)
        doc = events.event_document(self.reader, raw)
        programs = []
        for frame, level in zip(doc['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for prog in frame['programs']:
                data = blocks[prog['block_id']].data
                programs.append((prog, data[prog['program_offset']:prog['program_offset'] + prog['program_bytes']]))
        for prog in doc['global_events']:
            data = game.segments[prog['segment_id']].data
            programs.append((prog, data[prog['program_offset']:prog['program_offset'] + prog['program_bytes']]))
        counts = {'value': 0, 'unsupported_tokens': 0}
        for prog, data in programs:
            self.assertEqual(reconstruct_program(prog), data)
            for row in prog['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in (15, 22, 23, 45, 52, 53):
                            continue
                        at = q['offset'] + 6
                        out = q['expression_storage']
                        evaluation = out['constant_integer_evaluation']
                        eligible = data[at:at + 4] == b'\xff\x00\x08\x00' and data[at + 8:at + 10] == b'\0\0'
                        if eligible:
                            self.assertEqual(evaluation['status'], 'value')
                            self.assertEqual(evaluation['value_signed_i32'], int.from_bytes(data[at + 4:at + 8], 'little', signed=True))
                            self.assertEqual(evaluation['value_raw_u32'], int.from_bytes(data[at + 4:at + 8], 'little'))
                        else:
                            self.assertEqual(evaluation['status'], 'unsupported_tokens')
                            self.assertNotIn('value_signed_i32', evaluation)
                        counts[evaluation['status']] += 1
                        self.assertEqual(reconstruct_expression(out), bytes.fromhex(q['payload_hex']))
        self.assertEqual(counts, {'value': 3490, 'unsupported_tokens': 378})
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
