import collections
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import record, row, event_block, reconstruct_program
from test_event_expressions import token, expression
from test_value_table_actions import action_project


def condition(control=0, parameters=(), role='condition', kind=-1, opcode=-6):
    raw = bytearray(record(role, kind, opcode, 0, parameters))
    raw[9] = control
    return bytes(raw)


class RowBitTestSetTests(unittest.TestCase):
    def test_exact_signed_role_type_and_opcode_gate(self):
        for role in ('action', 'condition'):
            for kind in (-128, -2, -1, 0, 1, 127):
                for op in range(-128, 128):
                    r = events.decode_record(condition(role=role, kind=kind, opcode=op), role, 91, 2)
                    self.assertEqual('row_bit_test_set_condition_inputs' in r,
                                     role == 'condition' and kind == -1 and op == -6)
                    self.assertEqual(r['meaning'], 'unknown')

    def test_conditional_write_and_carry_preserve_other_fifteen_bits(self):
        v = events.decode_record(condition(), 'condition', 0, 0)['row_bit_test_set_condition_inputs']
        self.assertEqual(v['row_flags'], {'row_byte_offset': 4, 'bits': 16,
                                         'test_mask_raw_u16': 1, 'previous_flags': 'unknown'})
        branches = v['conditional_branches']
        self.assertEqual(branches['bit_0_clear'], {'return_carry': True, 'row_flags_written': True,
                                                 'write_bits': 16, 'or_mask_raw_u16': 1,
                                                 'flags_formula': 'previous_flags_u16 | 1'})
        self.assertEqual(branches['bit_0_set'], {'return_carry': False, 'row_flags_written': False})
        for flags in range(65536):
            selected = branches['bit_0_set' if flags & v['row_flags']['test_mask_raw_u16'] else 'bit_0_clear']
            self.assertEqual(selected['return_carry'], not bool(flags & 1))
            result = flags | selected.get('or_mask_raw_u16', 0)
            self.assertEqual(result & 0xfffe, flags & 0xfffe)
            self.assertEqual(result & 1, 1)
        self.assertFalse(v['runtime_resolution']); self.assertFalse(v['runtime_row_traversal'])
        self.assertEqual(v['row_pointer']['value'], 'unknown')
        self.assertEqual(v['row_flag_lifecycle'], 'unknown'); self.assertEqual(v['target_row'], 'unknown')
        for field in ('return_carry', 'final_row_flags', 'condition_result', 'row_result'):
            self.assertIsNone(v[field])

    def test_all_header_control_bytes_and_unused_faulting_parameters(self):
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800), token(255, struct.pack('<i', -1))])
        expected = events.decode_record(condition(), 'condition', 0, 0)['row_bit_test_set_condition_inputs']
        for control in range(256):
            for params in ([], [(999, b'opaque\xff')], [(39, bytes(4))], [(22, fault)]):
                raw = bytearray(condition(control, params)); raw[4:9] = b'\xff' * 5; raw[11:14] = b'\xa5' * 3
                r = events.decode_record(bytes(raw), 'condition', 12345, 4)
                self.assertEqual(r['row_bit_test_set_condition_inputs'], expected)
                self.assertFalse(expected['record_header_control_used']); self.assertEqual(expected['parameter_access'], 'none')
                self.assertEqual(r['header_hex'], raw[:14].hex())
                program = row([bytes(raw)], []) + bytes(2)
                self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)
                if params and params[0][0] == 22:
                    self.assertEqual(r['parameters'][0]['expression_storage']['constant_integer_evaluation']['status'], 'cpu_exception')

    def test_unused_parameters_still_require_valid_storage(self):
        for n in range(14):
            with self.assertRaises(project.InputError): events.decode_record(condition()[:n], 'condition', 0, 0)
        raw = bytearray(condition(parameters=[(999, b'own bytes')]))
        struct.pack_into('<H', raw, 14, 3)
        with self.assertRaisesRegex(project.InputError, 'parameter length'):
            events.decode_record(bytes(raw), 'condition', 0, 0)
        with self.assertRaisesRegex(project.InputError, 'trailing record bytes'):
            events.decode_record(condition() + b'x', 'condition', 0, 0)
        for n in range(4):
            with self.assertRaisesRegex(project.InputError, 'no complete runtime word'):
                events.decode_record(condition(parameters=[(39, bytes(n))]), 'condition', 0, 0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class RowBitTestSetContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_lossless_readable_and_immutable_bundle(self):
        program = row([condition(), condition(255, [(999, b'own opaque bytes')]), condition(opcode=-7)],
                      [condition(role='action')]) + bytes(2)
        raw = action_project(program); doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 41)
        self.assertTrue(doc['coverage']['row_bit_test_set_condition_inputs'])
        for k in ('opcode_semantics', 'parameter_semantics', 'global_reference_resolution', 'expression_evaluation'):
            self.assertFalse(doc['coverage'][k])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program); records = pr['rows'][0]['records']
            self.assertNotIn('row_bit_test_set_condition_inputs', records[2]); self.assertNotIn('row_bit_test_set_condition_inputs', records[3])
            self.assertEqual(records[0]['row_bit_test_set_condition_inputs'], records[1]['row_bit_test_set_condition_inputs'])
        self.assertEqual(events.readable(doc).count('ROW_BIT_TEST_SET_CONDITION '), 10)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc)); self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            p = bundle.save_bundle(manifest, files, Path(scratch)); old = {f.name: f.read_bytes() for f in p.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), p)
            changed = dict(files); changed['events.txt'] += b' '
            with self.assertRaises(project.InputError): bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({f.name: f.read_bytes() for f in p.iterdir()}, old)

    def test_late_malformed_unused_parameter_refused_before_output_and_report(self):
        program = row([condition(), condition(parameters=[(39, bytes(3))])], []) + bytes(2)
        raw = action_project(program)
        for module, flags in ((events, []), (events, ['--text']), (bundle, [])):
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, patch.object(bundle, 'save_bundle') as save_bundle, \
                    patch.object(project, 'report_fault') as report, patch('builtins.print') as output:
                self.assertEqual(module.main(), 2)
                self.assertTrue(any('no complete runtime word' in str(c) for c in output.call_args_list))
                save.assert_not_called(); save_bundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_source_walk(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes(); game = self.reader.read(raw); programs = []
        for level in game.levels():
            for block in self.reader.level_blocks(level.data)[1]:
                if block.data and block.ident == 4: programs.append(('frame', block.data[10:]))
        for segment in game.segments:
            if segment.ident == 3 and segment.data:
                start, size = struct.unpack_from('<II', segment.data, 12); programs.append(('global', segment.data[start:start + size]))
        observed = []; counts = collections.Counter(); total = 0
        for scope, data in programs:
            at = 0
            while (size := abs(struct.unpack_from('<h', data, at)[0])):
                nc, na = data[at + 2:at + 4]; rec = at + 14
                for i in range(nc + na):
                    extent = struct.unpack_from('<H', data, rec)[0]; total += 1
                    kind, op = struct.unpack_from('<bb', data, rec + 2)
                    if i < nc and kind == -1 and op == -6:
                        observed.append(data[rec:rec + extent].hex()); counts[scope] += 1
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        exported = []; doc = events.event_document(self.reader, raw)
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for r in pr['rows']:
                for rec in r['records']:
                    if 'row_bit_test_set_condition_inputs' in rec:
                        exported.append(rec['header_hex'] + ''.join(struct.pack('<HH', p['bytes'], p['type']).hex() + p['payload_hex'] for p in rec['parameters']))
                        v = rec['row_bit_test_set_condition_inputs']
                        self.assertFalse(v['runtime_resolution']); self.assertIsNone(v['return_carry'])
                        self.assertEqual(v['conditional_branches']['bit_0_clear']['return_carry'], True)
        self.assertEqual(exported, observed); self.assertEqual(total, 9306)
        self.assertEqual(observed, []); self.assertEqual(counts, {})
