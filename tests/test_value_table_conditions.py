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
from test_value_table_actions import action_project, literal


def condition(index=None, right=None, prefix=0, kind=-1, opcode=-8, role='condition'):
    if right is None:
        right = expression([token(255, struct.pack('<i', -1))], prefix=prefix)
    return record(role, kind, opcode, 0, [(22, index if index is not None else literal(1)), (23, right)])


def view(raw):
    return events.decode_record(raw, 'condition', 0, 0)['value_table_condition_inputs']


class ValueTableConditionTests(unittest.TestCase):
    def test_signed_index_aliases_full_dword_right_and_all_comparison_prefixes(self):
        names = ['equal', 'not_equal', 'less_or_equal', 'less', 'greater_or_equal', 'greater']
        for index in (-2147483648, -65537, -65536, -17, -1, 0, 1, 16, 17, 65535, 65536, 65537, 2147483647):
            for right in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
                for prefix in (*range(7), *range(0x8000, 0x8007), 0x7fff, 0xffff):
                    with self.subTest(index=index, right=right, prefix=prefix):
                        raw = condition(literal(index), expression([token(255, struct.pack('<i', right))], prefix=prefix))
                        v = view(raw); inputs = v['inputs']; c = v['comparison']
                        self.assertEqual(inputs['table_slot_index'], (index - 1) % 16)
                        self.assertEqual(inputs['table_byte_offset'], ((index - 1) % 16) * 4)
                        self.assertEqual(inputs['index_argument_u16'], index % 65536)
                        self.assertEqual(inputs['comparison_prefix_raw_u16'], prefix)
                        self.assertEqual(inputs['comparison_index_raw_u16'], prefix & 0x7fff)
                        self.assertEqual(inputs['opaque_high_bit_raw_u16'], prefix & 0x8000)
                        self.assertEqual((c['right_raw_u32'], c['right_signed_i32']), (right % 2**32, right))
                        self.assertEqual(c['operation'], names[prefix & 0x7fff] if prefix & 0x7fff < 6 else None)
                        self.assertEqual(c['status'], 'conditional_signed_comparison' if prefix & 0x7fff < 6 else 'outside_proven_comparison_table')
                        if prefix & 0x7fff < 6:
                            self.assertEqual((c['true_return_carry'], c['false_return_carry']), (True, False))
                        else:
                            self.assertNotIn('true_return_carry', c); self.assertNotIn('false_return_carry', c)
                        self.assertTrue(c['signed']); self.assertEqual(c['left_value'], 'unknown')
                        self.assertIsNone(c['condition_result']); self.assertFalse(v['runtime_resolution'])
                        self.assertFalse(v['operand_tags_checked_by_condition']); self.assertFalse(v['parameter_type_dispatch'])

    def test_compound_recursive_offsets_prefix_suffix_and_raw_reconstruction(self):
        index = expression([token(0x400), token(255, struct.pack('<i', -18))], suffix=bytes(37))
        right = expression([token(0xffff), token(255, struct.pack('<i', 2147483647)),
                            token(0x200), token(255, struct.pack('<i', 1)), token(0xfdff)],
                           prefix=0x8003, suffix=b'opaque\xff\0')
        raw = condition(index, right)
        out = events.decode_record(raw, 'condition', 4321, 7); v = out['value_table_condition_inputs']
        self.assertEqual(v['inputs']['right_parameter_record_offset'], 18 + len(index))
        self.assertEqual(v['inputs']['index_parameter_record_offset'], 14)
        self.assertEqual(v['inputs']['table_slot_index'], 1)
        self.assertEqual(v['comparison']['right_raw_u32'], 0x80000000)
        self.assertEqual(v['comparison']['operation'], 'less')
        self.assertEqual(out['meaning'], 'unknown')
        self.assertEqual([p['payload_hex'] for p in out['parameters']], [index.hex(), right.hex()])
        program = row([raw], []) + bytes(2)
        self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)

    def test_only_exact_system_condition_opcode_and_validated_parameter_layout(self):
        for kind, opcode, role in ((-2, -8, 'condition'), (1, -8, 'condition'), (-1, 8, 'condition'),
                                  (-1, -7, 'condition'), (-1, -8, 'action')):
            raw = condition(kind=kind, opcode=opcode, role=role)
            self.assertNotIn('value_table_condition_inputs', events.decode_record(raw, role, 0, 0))
        for params in ([], [(22, literal(1))], [(22, literal(1))] * 3,
                       [(23, literal(1)), (23, literal(1))], [(22, literal(1)), (22, literal(1))],
                       [(22, literal(1)), (999, b'opaque')]):
            v = view(record('condition', -1, -8, 0, params))
            self.assertEqual(v['inputs'], {'status': 'unsupported_parameter_shape'})
            self.assertEqual(v['comparison'], {'status': 'unresolved'})

    def test_ordered_faults_dynamic_string_and_stop_tail_remain_unresolved(self):
        dynamic = expression([token(0x3021, bytes(4))]); string = expression([token(0x3ff, b'abc\0')])
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800), token(255, struct.pack('<i', -1))])
        for index, right in ((dynamic, literal(1)), (literal(1), dynamic), (string, literal(1)),
                             (literal(1), string), (dynamic, fault),
                             (literal(1), expression([token(255, bytes(4)), token(0xfeff), token(0x12ff)])),
                             (literal(1), expression([token(255, struct.pack('<i', -2147483648)), token(0x800),
                                                     token(255, struct.pack('<i', -1)), token(0x200), token(0x3021, bytes(4))]))):
            self.assertEqual(view(condition(index, right))['comparison'], {'status': 'unresolved'})
        for index, right, stage in ((fault, literal(1), 'index'), (fault, fault, 'index'), (literal(1), fault, 'right_operand')):
            c = view(condition(index, right))['comparison']
            self.assertEqual(c, {'status': 'cpu_exception_before_table_read', 'stage': stage, 'exception_recovery': 'unknown'})


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ValueTableConditionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_readable_reconstruction_and_immutable_bundle(self):
        program = row([condition(prefix=p) for p in range(6)], [condition(role='action')]) + bytes(2)
        raw = action_project(program); doc = events.event_document(self.reader, raw)
        self.assertTrue(doc['coverage']['value_table_condition_inputs'])
        for k in ('opcode_semantics', 'parameter_semantics', 'expression_evaluation', 'global_reference_resolution'):
            self.assertFalse(doc['coverage'][k])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            self.assertNotIn('value_table_condition_inputs', pr['rows'][0]['records'][-1])
        self.assertEqual(events.readable(doc).count('VALUE_TABLE_CONDITION '), 30)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc)); self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            path = bundle.save_bundle(manifest, files, Path(scratch)); old = {p.name: p.read_bytes() for p in path.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), path)
            changed = dict(files); changed['events.json'] += b' '
            with self.assertRaises(project.InputError): bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, old)

    def test_late_invalid_expression_refused_before_output_or_report(self):
        raw = action_project(row([condition()], []) + bytes(2)); at = raw.rfind(token(255, struct.pack('<i', -1)))
        raw = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in ((events, []), (events, ['--text']), (bundle, [])):
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, patch.object(bundle, 'save_bundle') as save_bundle, \
                    patch.object(project, 'report_fault') as report, patch('builtins.print') as output:
                self.assertEqual(module.main(), 2)
                self.assertTrue(any('integer literal token has an unsupported extent' in str(c) for c in output.call_args_list))
                save.assert_not_called(); save_bundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_source_walk_and_storage(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes(); game = self.reader.read(raw); programs = []
        for level in game.levels():
            for block in self.reader.level_blocks(level.data)[1]:
                if block.data and block.ident == 4: programs.append(('frame', block.data[10:]))
        for segment in game.segments:
            if segment.ident == 3 and segment.data:
                start, size = struct.unpack_from('<II', segment.data, 12); programs.append(('global', segment.data[start:start + size]))
        observed = []; counts = collections.Counter(); all_records = 0
        for scope, data in programs:
            at = 0
            while (size := abs(struct.unpack_from('<h', data, at)[0])):
                nc, na = data[at + 2:at + 4]; rec = at + 14
                for i in range(nc + na):
                    extent = struct.unpack_from('<H', data, rec)[0]; all_records += 1
                    if i < nc and data[rec + 2:rec + 4] == b'\xff\xf8':
                        q = rec + 14; first, kind = struct.unpack_from('<HH', data, q); second = q + first
                        self.assertEqual((data[rec + 10], kind, struct.unpack_from('<H', data, second + 2)[0]), (2, 22, 23))
                        self.assertEqual(data[q + 6:q + 10], bytes.fromhex('ff000800'))
                        index = struct.unpack_from('<i', data, q + 10)[0]; prefix = struct.unpack_from('<H', data, second + 4)[0]
                        self.assertEqual(data[second + 6:second + 10], bytes.fromhex('ff000800'))
                        right = struct.unpack_from('<i', data, second + 10)[0]
                        observed.append((index, (index - 1) % 16, prefix, right)); counts[(scope, prefix)] += 1
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        doc = events.event_document(self.reader, raw); exported = []
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for row_ in pr['rows']:
                for rec in row_['records']:
                    if 'value_table_condition_inputs' in rec:
                        v = rec['value_table_condition_inputs']; a = v['inputs']; c = v['comparison']
                        self.assertFalse(v['runtime_resolution']); self.assertIsNone(c['condition_result'])
                        exported.append((a['index_evaluation']['value_signed_i32'], a['table_slot_index'], a['comparison_prefix_raw_u16'], c['right_signed_i32']))
        self.assertEqual(exported, observed); self.assertEqual(all_records, 9306); self.assertEqual(len(observed), 111)
        self.assertEqual(counts, {('frame', 0): 95, ('frame', 3): 4, ('frame', 5): 4, ('global', 0): 8})
