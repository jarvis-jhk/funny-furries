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


def action(opcode=6, offset=0, key=7, suffix=b'', role='action', kind=-1):
    payload = struct.pack('<I', offset) + (struct.pack('<H', key) if key is not None else b'') + suffix
    return record(role, kind, opcode, 0, [(39, payload)])


class GroupFlagActionTests(unittest.TestCase):
    def test_exact_signed_system_action_entries(self):
        for role in ('action', 'condition'):
            for kind in (-128, -2, -1, 0, 1, 127):
                for op in range(-128, 128):
                    out = events.decode_record(action(op, role=role, kind=kind), role, 37, 6)
                    matched = role == 'action' and kind == -1 and op in (6, 7)
                    self.assertEqual('group_flag_action_inputs' in out, matched)
                    if matched:
                        v = out['group_flag_action_inputs']
                        self.assertEqual(v['operation'], 'clear_bit_14' if op == 6 else 'set_bit_14')
                        self.assertEqual(v['row_flags']['and_mask_raw_u16'], 0xBFFF)
                        self.assertEqual(v['row_flags']['or_mask_raw_u16'], 0 if op == 6 else 0x4000)
                        self.assertFalse(v['runtime_resolution'])
                        self.assertIsNone(v['final_row_flags'])
                        self.assertEqual(v['editor_group_selection'], 'unresolved')
                    self.assertEqual(out['meaning'], 'unknown')

    def test_full_dword_offset_not_editor_key_or_source_row_target(self):
        for op in (6, 7):
            for offset in (0, 1, 0x7fff, 0x8000, 0xffff, 0x10000, 0x80000000, 0xffffffff):
                for key in (None, 0, 7, 0x4000, 0xffff):
                    raw = bytearray(action(op, offset, key, b'opaque\xff\0'))
                    raw[4:10] = bytes([0xa5]) * 6; raw[11] = 0xff
                    out = events.decode_record(bytes(raw), 'action', 100000, 5)
                    v = out['group_flag_action_inputs']; inp = v['inputs']
                    self.assertEqual(inp['target_offset_raw_u32'], offset)
                    self.assertEqual(inp['offset_record_byte_offset'], 16)
                    self.assertEqual(inp['offset_payload_byte_offset'], 0)
                    self.assertEqual(inp['runtime_base'], 'unknown')
                    self.assertIn('modulo 2^32', inp['target_address_formula'])
                    self.assertFalse(inp['editor_key_used_by_handler'])
                    self.assertFalse(inp['parameter_type_dispatch'])
                    self.assertEqual(v['target_rows'], 'unknown')
                    self.assertEqual(v['activation_semantics'], 'unknown')
                    program = row([], [bytes(raw)]) + bytes(2)
                    self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)
                    self.assertEqual(out['header_hex'], raw[:12].hex())

    def test_signed_step_next_marker_and_closing_row_contract(self):
        for op in (6, 7):
            v = events.decode_record(action(op), 'action', 0, 0)['group_flag_action_inputs']
            t = v['traversal']
            self.assertTrue(t['first_row_updated_before_step'])
            self.assertEqual(t['step_word_row_byte_offset'], 0)
            self.assertTrue(t['step_word_signed'])
            self.assertEqual(t['next_row_formula'], '(current_row_address - signed_i16_step_word) modulo 2^32')
            self.assertEqual((t['stop_word_next_row_byte_offset'], t['stop_word_raw_u16']), (16, 0xF5FF))
            self.assertTrue(t['stop_row_flags_also_updated'])
            self.assertFalse(t['nested_group_depth_checked'])
            self.assertFalse(t['runtime_bounds_or_cycle_guard'])
            self.assertIn('valid_terminating_runtime_rows', v['assumption'])

    def test_unsupported_shape_and_strict_validation_before_annotation(self):
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800),
                            token(255, struct.pack('<i', -1))])
        for params in ([], [(999, bytes(4))], [(39, bytes(4))] * 2, [(22, fault)]):
            raw = record('action', -1, 6, 0, params)
            out = events.decode_record(raw, 'action', 0, 0)
            self.assertEqual(out['group_flag_action_inputs']['inputs'], {'status': 'unsupported_parameter_shape'})
            self.assertIsNone(out['group_flag_action_inputs']['final_row_flags'])
        for n in range(4):
            with self.assertRaisesRegex(project.InputError, 'no complete runtime word'):
                events.decode_record(record('action', -1, 6, 0, [(39, bytes(n))]), 'action', 0, 0)
        raw = bytearray(action()); struct.pack_into('<H', raw, 12, 3)
        with self.assertRaisesRegex(project.InputError, 'parameter length'):
            events.decode_record(bytes(raw), 'action', 0, 0)
        with self.assertRaisesRegex(project.InputError, 'trailing record bytes'):
            events.decode_record(action() + b'x', 'action', 0, 0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class GroupFlagActionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_readable_lossless_and_immutable_bundle(self):
        program = row([action(role='condition')], [action(6), action(7, 0xffffffff), action(8)]) + bytes(2)
        raw = action_project(program); doc = events.event_document(self.reader, raw)
        self.assertTrue(doc['coverage']['group_flag_action_inputs'])
        for k in ('opcode_semantics', 'parameter_semantics', 'global_reference_resolution', 'expression_evaluation'):
            self.assertFalse(doc['coverage'][k])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            records = pr['rows'][0]['records']
            self.assertNotIn('group_flag_action_inputs', records[0]); self.assertNotIn('group_flag_action_inputs', records[3])
            self.assertEqual([r['group_flag_action_inputs']['operation'] for r in records[1:3]], ['clear_bit_14', 'set_bit_14'])
            for r in records[1:3]:
                self.assertEqual(r['parameters'][0]['group_parameter_storage']['status'], 'no_stored_word_match')
        self.assertEqual(events.readable(doc).count('GROUP_FLAG_ACTION '), 10)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            p = bundle.save_bundle(manifest, files, Path(scratch)); old = {f.name: f.read_bytes() for f in p.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), p)
            changed = dict(files); changed['events.txt'] += b' '
            with self.assertRaises(project.InputError): bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({f.name: f.read_bytes() for f in p.iterdir()}, old)

    def test_late_malformed_group_offset_refused_before_output_or_report(self):
        program = row([], [action(6), record('action', -1, 7, 0, [(39, bytes(3))])]) + bytes(2)
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
                    if i >= nc and kind == -1 and op in (6, 7):
                        self.assertEqual(data[rec + 10], 1)
                        self.assertEqual(struct.unpack_from('<HH', data, rec + 12), (10, 39))
                        offset = struct.unpack_from('<I', data, rec + 16)[0]
                        observed.append((op, data[rec:rec + extent].hex(), offset)); counts[(scope, op)] += 1
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        exported = []
        doc = events.event_document(self.reader, raw)
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for r in pr['rows']:
                for rec in r['records']:
                    if 'group_flag_action_inputs' in rec:
                        v = rec['group_flag_action_inputs']; offset = v['inputs']['target_offset_raw_u32']
                        payload = bytes.fromhex(rec['parameters'][0]['payload_hex'])
                        exported.append((rec['opcode'], rec['header_hex'] + struct.pack('<HH', rec['parameters'][0]['bytes'], 39).hex() + payload.hex(), offset))
                        self.assertFalse(v['runtime_resolution']); self.assertIsNone(v['final_row_flags'])
        self.assertEqual(exported, observed); self.assertEqual(total, 9306)
        self.assertEqual(len(observed), 115)
        self.assertEqual(counts, {('frame', 7): 95, ('global', 6): 12, ('global', 7): 8})
        self.assertEqual(sum(offset == 0 for _, _, offset in observed), 15)
        self.assertEqual(sum(offset != 0 for _, _, offset in observed), 100)
