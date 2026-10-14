import os
from pathlib import Path
import struct
import unittest

from tools import event_dump as events, project_index as project
from test_event_expressions import token, expression, expression_project, reconstruct_expression


def literal(value):
    return token(255, struct.pack('<i', value))


def view(argument, stop=0xFEFF, tail=()):
    raw = expression([token(0x1FF), *argument, token(stop), *tail])
    out = events.decode_expression(raw)
    return raw, out, out['tokens'][0]['random_inputs']['argument']


class ClosedRandomArgumentTests(unittest.TestCase):
    def test_arithmetic_wrapping_bound_words_priority_and_both_stops(self):
        cases = [([literal(1), token(0x200), literal(16)], 17),
                 ([literal(0), token(0x400), literal(1)], -1),
                 ([literal(2147483647), token(0x200), literal(1)], -2147483648),
                 ([literal(65536), token(0x600), literal(65536)], 0),
                 ([literal(-7), token(0x800), literal(3)], -2),
                 ([literal(-7), token(0xA00), literal(3)], -1),
                 ([literal(7), token(0x800), literal(0)], 0),
                 ([literal(-7), token(0xA00), literal(0)], -7),
                 ([literal(1), token(0x200), literal(2), token(0x600), literal(3)], 7),
                 ([literal(20), token(0x400), literal(7), token(0x400), literal(3)], 10)]
        for argument, expected in cases:
            for stop in (0xFEFF, 0xFDFF):
                with self.subTest(expected=expected, stop=stop):
                    raw, out, arg = view(argument, stop)
                    self.assertEqual(reconstruct_expression(out), raw)
                    self.assertEqual(arg['status'], 'closed_integer_and_stop')
                    self.assertEqual(arg['value_signed_i32'], expected)
                    self.assertEqual(arg['value_raw_u32'], expected % 2**32)
                    self.assertEqual(arg['rng_argument_u16'], expected % 65536)
                    self.assertEqual(arg['evaluation']['result_tag'], 0)
                    self.assertEqual(arg['token_ids'], list(range(1, len(argument) + 1)))
                    self.assertEqual(arg['stop_token_id'], len(argument) + 1)
                    self.assertEqual(arg['dispatch_return_cursor'], 'after_first_argument_token')
                    self.assertEqual(arg['dispatch_return_payload_offset'], 14)
                    self.assertEqual(out['constant_integer_evaluation']['status'], 'unsupported_tokens')
                    self.assertFalse(out['tokens'][0]['random_inputs']['runtime_resolution'])
                    self.assertNotIn('result', out['tokens'][0]['random_inputs'])

    def test_prefix_nested_recursion_and_stop_pairing(self):
        for inner_stop in (0xFEFF, 0xFDFF):
            for outer_stop in (0xFEFF, 0xFDFF):
                args = [token(0x400), token(0xFFFF), literal(1), token(0x200),
                        token(0xFFFF), literal(2), token(0x600), literal(3),
                        token(inner_stop), token(inner_stop)]
                raw, out, arg = view(args, outer_stop)
                self.assertEqual(arg['value_signed_i32'], -7)
                self.assertEqual(arg['rng_argument_u16'], 65529)
                self.assertEqual(arg['stop_token_id'], 11)
                self.assertEqual(arg['dispatch_return_payload_offset'], 10)
                self.assertEqual(reconstruct_expression(out), raw)
        _, _, arg = view([token(0x400), literal(-2147483648)])
        self.assertEqual(arg['value_signed_i32'], -2147483648)
        self.assertEqual(arg['dispatch_return_payload_offset'], 10)

    def test_cpu_fault_has_no_bound_result_or_normal_return_cursor(self):
        for opcode in (0x800, 0xA00):
            raw, out, arg = view([literal(-2147483648), token(opcode), literal(-1)])
            self.assertEqual(arg['status'], 'cpu_exception')
            self.assertEqual(arg['evaluation']['fault'], 'x86_divide_error')
            self.assertEqual(arg['evaluation']['operator_token_id'], 2)
            for key in ('rng_argument_u16', 'value_signed_i32', 'value_raw_u32',
                        'dispatch_return_cursor', 'dispatch_return_payload_offset'):
                self.assertNotIn(key, arg)
            self.assertEqual(reconstruct_expression(out), raw)

    def test_unsupported_forms_and_dynamic_fault_tail_are_not_evaluated(self):
        arguments = [[], [token(0x1FF)], [token(0x2FF)], [token(0x3FF, b'x\0')],
                     [literal(1), token(0x200)], [token(0x400), token(0x400), literal(1)],
                     [token(0xFFFF), literal(1)],
                     [literal(-2147483648), token(0x800), literal(-1), token(0x200), token(0x1FF)]]
        for args in arguments:
            raw, out, arg = view(args)
            self.assertEqual(arg, {'status': 'unsupported_shape'})
            self.assertEqual(reconstruct_expression(out), raw)
        for args in ([literal(1), token(0x200), literal(2)],
                     [token(0xFFFF), literal(1), token(0xFDFF)]):
            raw = expression([token(0x1FF), *args], suffix=token(0xFEFF))
            out = events.decode_expression(raw)
            self.assertEqual(out['tokens'][0]['random_inputs']['argument'], {'status': 'unsupported_shape'})
            self.assertEqual(reconstruct_expression(out), raw)

    def test_first_top_level_stop_bounds_argument_and_legacy_view_is_unchanged(self):
        _, _, arg = view([literal(1), token(0x200), literal(2)], tail=[token(0x12FF)])
        self.assertEqual(arg['value_signed_i32'], 3)
        self.assertEqual(arg['stop_token_id'], 4)
        _, out, arg = view([literal(17)], tail=[token(0x12FF)])
        self.assertEqual(arg['status'], 'adjacent_integer_literal_and_stop')
        self.assertEqual(arg['dispatch_return_cursor'], 'unconsumed_stop_token')
        self.assertNotIn('evaluation', arg)
        self.assertNotIn('dispatch_return_payload_offset', arg)
        self.assertEqual(arg['rng_argument_u16'], 17)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ClosedRandomContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_roles_types_text_reconstruction_and_bundle(self):
        from tools import export_project as bundle
        from test_event_dump import reconstruct_program
        for kind in sorted(events.EXPRESSION_TYPES):
            payload = expression([token(0x1FF), literal(1), token(0x200), literal(16), token(0xFEFF)])
            raw, program = expression_project(payload)
            old = struct.pack('<HH', len(payload) + 4, 22); new = struct.pack('<HH', len(payload) + 4, kind)
            raw = raw.replace(old, new); program = program.replace(old, new)
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_random_closed_argument_inputs'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                self.assertEqual(reconstruct_program(pr), program)
                for rec in pr['rows'][0]['records']:
                    arg = rec['parameters'][0]['expression_storage']['tokens'][0]['random_inputs']['argument']
                    self.assertEqual((arg['value_signed_i32'], arg['rng_argument_u16']), (17, 17))
            self.assertEqual(events.readable(doc).count('"status": "closed_integer_and_stop"'), 10)
            manifest, files = bundle.research_bundle(self.reader, raw)
            self.assertEqual(files['events.json'], bundle.json_bytes(doc))
            self.assertEqual(files['events.txt'], events.readable(doc).encode())
            self.assertFalse(manifest['coverage']['behaviour'])
            self.assertEqual(bundle.research_bundle(self.reader, raw), (manifest, files))

    def test_late_bad_closed_argument_refused_before_output_and_reporting(self):
        from tools import export_project as bundle
        from unittest.mock import patch
        payload = expression([token(0x1FF), literal(1), token(0x200), literal(2), token(0xFEFF)])
        raw, _ = expression_project(payload)
        at = raw.rfind(literal(2)); raw = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in ((events, []), (events, ['--text']), (bundle, [])):
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as save_bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); save_bundle.assert_not_called(); report.assert_not_called()
