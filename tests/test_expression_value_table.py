import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


def value_expression(value, stop=0xFEFF):
    return expression([token(0x2FF), token(0xFF, struct.pack('<i', value)), token(stop)])


class ValueTableInputTests(unittest.TestCase):
    def test_all_slots_low_word_signed_boundaries_and_both_stops(self):
        values = list(range(33)) + [-2147483648, -65537, -65536, -17, -16, -1,
                                    65535, 65536, 65537, 2147483647]
        for value in values:
            for stop in (0xFEFF, 0xFDFF):
                with self.subTest(value=value, stop=stop):
                    raw = value_expression(value, stop)
                    out = events.decode_expression(raw)
                    self.assertEqual(reconstruct_expression(out), raw)
                    view = out['tokens'][0]['value_table_inputs']; arg = view['argument']
                    self.assertEqual((arg['value_signed_i32'], arg['value_raw_u32'], arg['argument_u16']),
                                     (value, value & 0xFFFFFFFF, value % 65536))
                    self.assertEqual((arg['table_slot_index'], arg['table_byte_offset']),
                                     ((value - 1) % 16, ((value - 1) % 16) * 4))
                    self.assertEqual((arg['literal_token_id'], arg['stop_token_id']), (1, 2))
                    self.assertEqual(arg['dispatch_return_cursor'], 'unconsumed_stop_token')
                    self.assertEqual((view['slots'], view['entry_bytes'], view['normal_result_tag']), (16, 4, 0))
                    self.assertEqual(view['slot_formula'], '(argument_u16 - 1) & 0xF')
                    self.assertEqual(view['runtime_values'], 'unknown')
                    self.assertEqual(view['table_meaning'], 'unknown')
                    self.assertFalse(view['runtime_resolution'])
                    self.assertEqual(out['constant_integer_evaluation']['status'], 'unsupported_tokens')
                    self.assertNotIn('value', out); self.assertNotIn('result', view)
                    self.assertEqual(out['tokens'][0]['meaning'], 'unknown')

    def test_zero_and_aliases_use_last_slot_without_clamping(self):
        for value in (0, 16, -16, 65536, -65536):
            arg = events.decode_expression(value_expression(value))['tokens'][0]['value_table_inputs']['argument']
            self.assertEqual(arg['table_slot_index'], 15)
            self.assertEqual(arg['table_byte_offset'], 60)
        for value in (1, 17, -15, 65537, -65535):
            arg = events.decode_expression(value_expression(value))['tokens'][0]['value_table_inputs']['argument']
            self.assertEqual(arg['table_slot_index'], 0)

    def test_exact_code_extent_and_opaque_neighbours(self):
        for code in (0xFF02, 0x1FF, 0x3FF, 0x202, 0x12FF):
            raw = token(code, b'x\0\0\0') if code != 0x1FF else token(code)
            self.assertNotIn('value_table_inputs', events.decode_expression(expression([raw]))['tokens'][0])
        for extent in (b'x', bytes(4), b'opaque' * 8):
            with self.assertRaises(project.InputError):
                events.decode_expression(expression([token(0x2FF, extent)]))

    def test_dynamic_recursive_compound_missing_and_suffix_do_not_supply_argument(self):
        tails = [[], [token(0xFF, bytes(4))], [token(0x3FF, b'x\0'), token(0xFEFF)],
                 [token(0xFF, bytes(4)), token(0x200), token(0xFF, bytes(4)), token(0xFEFF)],
                 [token(0xFFFF), token(0xFF, bytes(4)), token(0xFEFF), token(0xFDFF)],
                 [token(0x2FF), token(0xFEFF)]]
        for tail in tails:
            raw = expression([token(0x2FF), *tail], suffix=token(0xFF, bytes(4)) + token(0xFEFF))
            out = events.decode_expression(raw)
            self.assertEqual(out['tokens'][0]['value_table_inputs']['argument'], {'status': 'unsupported_shape'})
            self.assertEqual(reconstruct_expression(out), raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ValueTableContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_both_roles_every_expression_type_text_and_other_views(self):
        payload = value_expression(0)
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, _ = expression_project(payload)
            raw = raw.replace(struct.pack('<HH', 4 + len(payload), 22), struct.pack('<HH', 4 + len(payload), kind))
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_value_table_inputs'])
            for key in ('expression_evaluation', 'parameter_semantics', 'opcode_semantics', 'global_reference_resolution'):
                self.assertFalse(doc['coverage'][key])
            for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                for rec in pr['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['expression_storage']['tokens'][0]['value_table_inputs']['argument']['table_slot_index'], 15)
                    if kind == 15:
                        self.assertEqual(q['scalar_getter_storage']['conditional_getter_return']['eax_raw_u32'], 0xFEDC)
                    if kind in (22, 45, 46):
                        self.assertEqual(q['expression_storage']['constant_integer_evaluation']['status'], 'unsupported_tokens')
            self.assertEqual(events.readable(doc).count('"operation": "runtime_value_table_read"'), 10)

    def test_late_bad_extent_refused_before_json_text_bundle_or_fault_report(self):
        raw, _ = expression_project(value_expression(12))
        at = raw.rfind(token(0x2FF))
        raw = raw[:at + 2] + struct.pack('<H', 6) + raw[at + 4:]
        for module, flags in ((events, []), (events, ['--text']), (bundle, [])):
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as save_bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); save_bundle.assert_not_called(); report.assert_not_called()

    def test_lossless_program_bundle_repeat_and_immutable_output(self):
        raw, program = expression_project(value_expression(12))
        doc = events.event_document(self.reader, raw)
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            path = bundle.save_bundle(manifest, files, Path(scratch))
            before = {p.name: p.read_bytes() for p in path.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), path)
            changed = dict(files); changed['events.json'] += b' '
            with self.assertRaises(project.InputError):
                bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, before)

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_bytes_independent_walk_all_value_table_arguments(self):
        from collections import Counter
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        game = self.reader.read(raw); programs = []
        for level in game.levels():
            for block in self.reader.level_blocks(level.data)[1]:
                if block.data and block.ident == 4:
                    programs.append(('frame', block.data[10:]))
        for segment in game.segments:
            if segment.ident == 3 and segment.data:
                start, size = struct.unpack_from('<II', segment.data, 12)
                programs.append(('global', segment.data[start:start + size]))
        observed = []; roles = Counter(); scopes = Counter(); count = 0
        for scope, data in programs:
            at = 0
            while (size := abs(struct.unpack_from('<h', data, at)[0])):
                nc, na = data[at + 2:at + 4]; rec = at + 14
                for i in range(nc + na):
                    extent = struct.unpack_from('<H', data, rec)[0]; q = rec + (14 if i < nc else 12)
                    for _ in range(data[rec + 10]):
                        n, kind = struct.unpack_from('<HH', data, q); count += 1
                        if kind in {15, 22, 23, 45, 46, 52, 53}:
                            cursor = q + 6
                            while (code := struct.unpack_from('<H', data, cursor)[0]):
                                length = struct.unpack_from('<H', data, cursor + 2)[0]
                                if code == 0x2FF:
                                    self.assertEqual(data[cursor:cursor + 8], bytes.fromhex('ff020400ff000800'))
                                    self.assertEqual(data[cursor + 12:cursor + 16], bytes.fromhex('fffe0400'))
                                    value = struct.unpack_from('<i', data, cursor + 8)[0]
                                    observed.append((value, (value - 1) % 16, ((value - 1) % 16) * 4))
                                    roles['condition' if i < nc else 'action'] += 1; scopes[scope] += 1
                                cursor += length
                        q += n
                    self.assertEqual(q, rec + extent); rec += extent
                self.assertEqual(rec, at + size); at += size
        doc = events.event_document(self.reader, raw); exported = []
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        for t in q.get('expression_storage', {}).get('tokens', []):
                            if 'value_table_inputs' in t:
                                arg = t['value_table_inputs']['argument']
                                self.assertEqual(arg['status'], 'adjacent_integer_literal_and_stop')
                                exported.append((arg['value_signed_i32'], arg['table_slot_index'], arg['table_byte_offset']))
        self.assertEqual(exported, observed)
        self.assertEqual(len(observed), 45)
        self.assertEqual(count, 8160)
        self.assertEqual(Counter(value for value, _, _ in observed),
                         {1: 4, 2: 6, 3: 4, 4: 4, 5: 4, 6: 4, 7: 7, 9: 6, 10: 6})
        self.assertEqual(roles, {'action': 43, 'condition': 2})
        self.assertEqual(scopes, {'frame': 41, 'global': 4})
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
