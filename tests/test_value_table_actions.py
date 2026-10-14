import collections
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import record, row, event_block, global_block, reconstruct_program
from test_event_expressions import token, expression


def literal(value, suffix=b''):
    return expression([token(255, struct.pack('<i', value))], suffix=suffix)


def action(opcode=3, index=None, operand=None, kind=-1, role='action'):
    return record(role, kind, opcode, 0, [(22, index if index is not None else literal(1)),
                                         (22, operand if operand is not None else literal(-1))])


def view(raw):
    return events.decode_record(raw, 'action', 0, 0)['value_table_action_inputs']


def action_project(program):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    frames = [bytes(0xB8) + block(0x8004, event_block(program)) for _ in range(4)]
    header = bytearray(0x166 + 4 * len(frames))
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, len(frames))
    body = block(3, global_block(program))
    for i, frame in enumerate(frames):
        struct.pack_into('<I', header, 0x166 + 4 * i, len(header) + len(body) + 6)
        body += block(0x8008 if i == len(frames) - 1 else 8, frame)
    return bytes(header) + body


class ValueTableActionTests(unittest.TestCase):
    def test_exact_opcode_order_signed_words_aliases_and_dword_operand(self):
        for opcode, operation in ((3, 'set'), (4, 'subtract'), (5, 'add')):
            for index in (-2147483648, -65537, -65536, -17, -1, 0, 1, 16, 17, 65535, 65536, 65537, 2147483647):
                for operand in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
                    with self.subTest(opcode=opcode, index=index, operand=operand):
                        v = view(action(opcode, literal(index), literal(operand)))
                        self.assertEqual(v['operation'], operation)
                        self.assertEqual(v['target'], 'runtime_value_table')
                        self.assertFalse(v['runtime_resolution'])
                        self.assertEqual(v['table_meaning'], 'unknown')
                        self.assertFalse(v['operand_tags_checked_by_action'])
                        self.assertFalse(v['parameter_type_dispatch'])
                        self.assertEqual(v['inputs']['index_argument_u16'], index % 65536)
                        self.assertEqual(v['inputs']['table_slot_index'], (index - 1) % 16)
                        self.assertEqual(v['inputs']['table_byte_offset'], ((index - 1) % 16) * 4)
                        w = v['write']
                        self.assertEqual(w['status'], 'conditional_numeric_write')
                        self.assertEqual((w['operand_raw_u32'], w['operand_signed_i32']),
                                         (operand % 2**32, operand))
                        if opcode == 3:
                            self.assertEqual(w['stored_value_raw_u32'], operand % 2**32)
                        else:
                            self.assertNotIn('stored_value_raw_u32', w)
                            self.assertEqual(w['previous_value'], 'unknown')
                            self.assertIn(' - ' if opcode == 4 else ' + ', w['result_formula'])

    def test_variable_parameter_sizes_suffixes_prefix_and_preserved_raw_storage(self):
        index = expression([token(0x400), token(255, struct.pack('<i', -18))],
                           prefix=0xBEEF, suffix=bytes(37))
        operand = expression([token(0xFFFF), token(255, struct.pack('<i', 2147483647)),
                              token(0x200), token(255, struct.pack('<i', 1)), token(0xFDFF)],
                             prefix=0xCAFE, suffix=b'opaque\xff\0')
        raw = action(3, index, operand)
        out = events.decode_record(raw, 'action', 1234, 7)
        v = out['value_table_action_inputs']
        self.assertEqual(v['inputs']['operand_parameter_record_offset'], 16 + len(index))
        self.assertEqual(v['inputs']['table_slot_index'], 1)
        self.assertEqual(v['write']['stored_value_raw_u32'], 0x80000000)
        program = row([], [raw]) + bytes(2)
        self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)
        self.assertEqual(out['meaning'], 'unknown')
        self.assertEqual([p['payload_hex'] for p in out['parameters']], [index.hex(), operand.hex()])

    def test_only_exact_action_system_type_and_opcode_have_annotation(self):
        for kind, opcode, role in ((-2, 3, 'action'), (2, 3, 'action'), (-1, -3, 'action'),
                                    (-1, 2, 'action'), (-1, 6, 'action'), (-1, 3, 'condition')):
            raw = action(opcode, kind=kind, role=role)
            self.assertNotIn('value_table_action_inputs', events.decode_record(raw, role, 0, 0))
        for params in ([], [(22, literal(1))], [(22, literal(1))] * 3,
                       [(15, literal(1)), (22, literal(1))],
                       [(22, literal(1)), (999, b'opaque')]):
            v = view(record('action', -1, 3, 0, params))
            self.assertEqual(v['inputs'], {'status': 'unsupported_parameter_shape'})
            self.assertEqual(v['write'], {'status': 'unresolved'})

    def test_dynamic_string_stop_tail_and_ordered_cpu_faults_stay_explicit(self):
        dynamic = expression([token(0x3021, bytes(4))])
        string = expression([token(0x3FF, b'abc\0')])
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800),
                            token(255, struct.pack('<i', -1))])
        for index, operand in ((dynamic, literal(1)), (literal(1), dynamic),
                               (string, literal(1)), (literal(1), string),
                               (dynamic, fault),
                               (literal(1), expression([token(255, bytes(4)), token(0xFEFF), token(0x12FF)]))):
            v = view(action(index=index, operand=operand))
            self.assertEqual(v['write'], {'status': 'unresolved'})
        for index, operand, stage in ((fault, literal(1), 'index'), (fault, fault, 'index'),
                                      (literal(1), fault, 'operand')):
            v = view(action(index=index, operand=operand))
            self.assertEqual(v['write'], {'status': 'cpu_exception_before_write', 'stage': stage,
                                         'exception_recovery': 'unknown'})
            self.assertNotIn('stored_value_raw_u32', v['write'])
        # Unknown dynamic tail prevents an early arithmetic fault claim.
        apparent = expression([token(255, struct.pack('<i', -2147483648)), token(0x800),
                               token(255, struct.pack('<i', -1)), token(0x200), token(0x3021, bytes(4))])
        self.assertEqual(view(action(index=apparent))['write'], {'status': 'unresolved'})


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ValueTableActionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_text_lossless_bundle_repeat_and_previous_views(self):
        program = row([action(3, role='condition')], [action(op) for op in (3, 4, 5)]) + bytes(2)
        raw = action_project(program)
        doc = events.event_document(self.reader, raw)
        self.assertTrue(doc['coverage']['value_table_action_inputs'])
        for key in ('opcode_semantics', 'parameter_semantics', 'expression_evaluation', 'global_reference_resolution'):
            self.assertFalse(doc['coverage'][key])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            self.assertNotIn('value_table_action_inputs', pr['rows'][0]['records'][0])
            self.assertEqual([r['value_table_action_inputs']['operation'] for r in pr['rows'][0]['records'][1:]],
                             ['set', 'subtract', 'add'])
        self.assertEqual(events.readable(doc).count('VALUE_TABLE_ACTION '), 15)
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

    def test_late_invalid_expression_refused_before_json_text_bundle_and_reporting(self):
        raw = action_project(row([], [action()]) + bytes(2))
        at = raw.rfind(token(255, struct.pack('<i', -1)))
        raw = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in ((events, []), (events, ['--text']), (bundle, [])):
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as save_bundle, \
                    patch.object(project, 'report_fault') as report:
                with patch('builtins.print') as output:
                    self.assertEqual(module.main(), 2)
                self.assertTrue(any('integer literal token has an unsupported extent' in str(call)
                                    for call in output.call_args_list))
                save.assert_not_called(); save_bundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_record_walk_and_raw_index_operand_storage(self):
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
        observed = []; counts = collections.Counter(); all_records = 0
        for scope, data in programs:
            at = 0
            while (size := abs(struct.unpack_from('<h', data, at)[0])):
                nc, na = data[at + 2:at + 4]; rec = at + 14
                for i in range(nc + na):
                    extent = struct.unpack_from('<H', data, rec)[0]; all_records += 1
                    if i >= nc and data[rec + 2] == 255 and data[rec + 3] in (3, 4, 5):
                        op = data[rec + 3]; q = rec + 12
                        first_size, first_kind = struct.unpack_from('<HH', data, q)
                        second_size, second_kind = struct.unpack_from('<HH', data, q + first_size)
                        self.assertEqual((data[rec + 10], first_kind, second_kind), (2, 22, 22))
                        self.assertEqual(q + first_size + second_size, rec + extent)
                        self.assertEqual(data[q + 6:q + 10], bytes.fromhex('ff000800'))
                        index = struct.unpack_from('<i', data, q + 10)[0]
                        operand_start = q + first_size
                        closed = data[operand_start + 6:operand_start + 10] == bytes.fromhex('ff000800')
                        operand = struct.unpack_from('<i', data, operand_start + 10)[0] if closed else None
                        observed.append((op, index, (index - 1) % 16, operand))
                        counts[(scope, op, 'closed' if closed else 'dynamic')] += 1
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        doc = events.event_document(self.reader, raw); exported = []
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for row_ in pr['rows']:
                for rec in row_['records']:
                    if 'value_table_action_inputs' in rec:
                        v = rec['value_table_action_inputs']; inputs = v['inputs']; w = v['write']
                        self.assertFalse(v['runtime_resolution'])
                        operand = w.get('operand_signed_i32')
                        if operand is None:
                            self.assertEqual(w, {'status': 'unresolved'})
                        exported.append((rec['opcode'], inputs['index_evaluation']['value_signed_i32'],
                                         inputs['table_slot_index'], operand))
        self.assertEqual(exported, observed)
        self.assertEqual(all_records, 9306)
        self.assertEqual(len(observed), 62)
        self.assertEqual(counts, {('frame', 3, 'closed'): 25, ('frame', 3, 'dynamic'): 17,
                                  ('frame', 4, 'closed'): 4, ('frame', 5, 'closed'): 4,
                                  ('global', 3, 'closed'): 12})
