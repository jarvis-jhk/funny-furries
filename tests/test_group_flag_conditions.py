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


def condition(offset=0, key=7, control=0, suffix=b'', role='condition', kind=-1, opcode=-12):
    payload = struct.pack('<I', offset) + (struct.pack('<H', key) if key is not None else b'') + suffix
    raw = bytearray(record(role, kind, opcode, 0, [(39, payload)]))
    raw[9] = control
    return bytes(raw)


class GroupFlagConditionTests(unittest.TestCase):
    def test_exact_signed_role_type_and_opcode_gate(self):
        for role in ('action', 'condition'):
            for kind in (-128, -2, -1, 0, 1, 127):
                for op in range(-128, 128):
                    r = events.decode_record(condition(role=role, kind=kind, opcode=op), role, 91, 2)
                    self.assertEqual('group_flag_condition_inputs' in r,
                                     role == 'condition' and kind == -1 and op == -12)
                    self.assertEqual(r['meaning'], 'unknown')

    def test_all_header_bytes_conditional_carry_and_opaque_row(self):
        for control in range(256):
            raw = bytearray(condition(control=control)); raw[4:9] = b'\xff' * 5; raw[11:14] = b'\xa5' * 3
            r = events.decode_record(bytes(raw), 'condition', 0, 0)
            v = r['group_flag_condition_inputs']; h = v['header_control']; ret = v['conditional_return']
            self.assertEqual(h, {'record_byte_offset': 9, 'raw_u8': control,
                                 'return_control_mask_raw_u8': 1, 'return_control_bit': control & 1})
            self.assertEqual(ret['row_bit_14_clear_carry'], not bool(control & 1))
            self.assertEqual(ret['row_bit_14_set_carry'], bool(control & 1))
            self.assertFalse(ret['row_flags_written']); self.assertFalse(ret['runtime_row_traversal'])
            self.assertEqual(v['row_flags'], {'row_byte_offset': 4, 'bits': 16,
                                             'test_mask_raw_u16': 0x4000, 'value': 'unknown'})
            self.assertFalse(v['runtime_resolution'])
            for field in ('return_carry', 'condition_result', 'row_result'): self.assertIsNone(v[field])
            self.assertEqual(v['target_row'], 'unknown'); self.assertEqual(v['editor_group_selection'], 'unresolved')
            self.assertIn('nonzero_esi', v['assumption']); self.assertEqual(r['header_hex'], raw[:14].hex())

    def test_full_dword_offset_at_condition_not_action_offset(self):
        for offset in (0, 1, 0x7fff, 0x8000, 0xffff, 0x10000, 0x80000000, 0xffffffff):
            for key in (None, 0, 7, 0xffff):
                raw = condition(offset, key, suffix=b'opaque\xff\0')
                v = events.decode_record(raw, 'condition', 20000, 5)['group_flag_condition_inputs']
                inp = v['inputs']
                self.assertEqual(inp['target_offset_raw_u32'], offset)
                self.assertEqual(inp['offset_record_byte_offset'], 18)
                self.assertEqual(inp['offset_payload_byte_offset'], 0)
                self.assertFalse(inp['editor_key_used_by_handler']); self.assertFalse(inp['parameter_type_dispatch'])
                self.assertEqual(inp['runtime_base'], 'unknown'); self.assertIn('modulo 2^32', inp['target_address_formula'])
                program = row([raw], []) + bytes(2)
                self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)

    def test_unsupported_shapes_and_strict_validation(self):
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800), token(255, struct.pack('<i', -1))])
        for params in ([], [(999, bytes(4))], [(39, bytes(4))] * 2, [(22, fault)]):
            r = events.decode_record(record('condition', -1, -12, 0, params), 'condition', 0, 0)
            v = r['group_flag_condition_inputs']
            self.assertEqual(v['inputs'], {'status': 'unsupported_parameter_shape'})
            self.assertIsNone(v['return_carry']); self.assertIsNone(v['condition_result'])
        for n in range(4):
            with self.assertRaisesRegex(project.InputError, 'no complete runtime word'):
                events.decode_record(record('condition', -1, -12, 0, [(39, bytes(n))]), 'condition', 0, 0)
        raw = bytearray(condition()); struct.pack_into('<H', raw, 14, 3)
        with self.assertRaisesRegex(project.InputError, 'parameter length'): events.decode_record(bytes(raw), 'condition', 0, 0)
        with self.assertRaisesRegex(project.InputError, 'trailing record bytes'): events.decode_record(condition() + b'x', 'condition', 0, 0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class GroupFlagConditionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_lossless_readable_and_immutable_bundle(self):
        program = row([condition(control=0), condition(0xffffffff, control=255), condition(opcode=-11)],
                      [condition(role='action')]) + bytes(2)
        raw = action_project(program); doc = events.event_document(self.reader, raw)
        self.assertTrue(doc['coverage']['group_flag_condition_inputs'])
        for k in ('opcode_semantics', 'parameter_semantics', 'global_reference_resolution', 'expression_evaluation'):
            self.assertFalse(doc['coverage'][k])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program); records = pr['rows'][0]['records']
            self.assertNotIn('group_flag_condition_inputs', records[2]); self.assertNotIn('group_flag_condition_inputs', records[3])
            self.assertEqual([r['group_flag_condition_inputs']['conditional_return']['row_bit_14_set_carry'] for r in records[:2]], [False, True])
        self.assertEqual(events.readable(doc).count('GROUP_FLAG_CONDITION '), 10)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc)); self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            p = bundle.save_bundle(manifest, files, Path(scratch)); old = {f.name: f.read_bytes() for f in p.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), p)
            changed = dict(files); changed['events.txt'] += b' '
            with self.assertRaises(project.InputError): bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({f.name: f.read_bytes() for f in p.iterdir()}, old)

    def test_late_malformed_group_condition_refused_before_output_and_report(self):
        program = row([condition(), record('condition', -1, -12, 0, [(39, bytes(3))])], []) + bytes(2)
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
                    if i < nc and kind == -1 and op == -12:
                        self.assertEqual(data[rec + 10], 1)
                        self.assertEqual(struct.unpack_from('<HH', data, rec + 14), (10, 39))
                        observed.append((data[rec:rec + extent].hex(), struct.unpack_from('<I', data, rec + 18)[0], data[rec + 9])); counts[scope] += 1
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        exported = []; doc = events.event_document(self.reader, raw)
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for r in pr['rows']:
                for rec in r['records']:
                    if 'group_flag_condition_inputs' in rec:
                        v = rec['group_flag_condition_inputs']; payload = bytes.fromhex(rec['parameters'][0]['payload_hex'])
                        exported.append((rec['header_hex'] + struct.pack('<HH', rec['parameters'][0]['bytes'], 39).hex() + payload.hex(),
                                         v['inputs']['target_offset_raw_u32'], v['header_control']['raw_u8']))
                        self.assertFalse(v['runtime_resolution']); self.assertIsNone(v['return_carry'])
        self.assertEqual(exported, observed); self.assertEqual(total, 9306)
        self.assertEqual(len(observed), 44); self.assertEqual(counts, {'frame': 40, 'global': 4})
