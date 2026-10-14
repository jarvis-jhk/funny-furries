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


class ConstantConditionTests(unittest.TestCase):
    def test_only_two_exact_signed_system_condition_entries(self):
        for role in ('condition', 'action'):
            for kind in (-128, -2, -1, 0, 1, 127):
                for opcode in range(-128, 128):
                    with self.subTest(role=role, kind=kind, opcode=opcode):
                        out = events.decode_record(record(role, kind, opcode, 0, []), role, 41, 7)
                        matched = role == 'condition' and kind == -1 and opcode in (-1, -2)
                        self.assertEqual('constant_condition_return' in out, matched)
                        if matched:
                            v = out['constant_condition_return']
                            self.assertEqual(v['return_carry'], opcode == -1)
                            self.assertEqual(v['status'], 'conditional_fixed_carry_return')
                            self.assertEqual(v['assumption'], 'nonzero_esi_system_dispatch_reaches_handler')
                            self.assertIsNone(v['condition_result']); self.assertIsNone(v['row_result'])
                            self.assertFalse(v['runtime_resolution'])
                        self.assertEqual(out['meaning'], 'unknown')

    def test_opaque_header_and_unused_parameters_preserved_without_evaluation(self):
        fault = expression([token(255, struct.pack('<i', -2147483648)), token(0x800),
                            token(255, struct.pack('<i', -1))])
        for opcode in (-1, -2):
            for reference in (-32768, -1, 0, 32767):
                for flags in (0, 1, 0x80, 0xff):
                    raw = bytearray(record('condition', -1, opcode, reference,
                                           [(999, b'own opaque data'), (22, fault)]))
                    raw[6:10] = bytes([flags]) * 4; raw[11:14] = bytes([flags]) * 3
                    out = events.decode_record(bytes(raw), 'condition', 1234, 6)
                    self.assertEqual(out['header_hex'], raw[:14].hex())
                    self.assertEqual(out['parameters'][0]['payload_hex'], b'own opaque data'.hex())
                    self.assertEqual(out['parameters'][1]['expression_storage']['constant_integer_evaluation']['status'], 'cpu_exception')
                    self.assertEqual(out['constant_condition_return']['return_carry'], opcode == -1)
                    self.assertEqual(out['constant_condition_return']['parameter_access'], 'none')
                    self.assertEqual(out['constant_condition_return']['runtime_state_access'], 'none')
                    program = row([bytes(raw)], []) + bytes(2)
                    self.assertEqual(reconstruct_program(events.decode_program(event_block(program))), program)

    def test_fixed_return_does_not_bypass_record_or_parameter_validation(self):
        for opcode in (-1, -2):
            raw = bytearray(record('condition', -1, opcode, 0, [(999, b'own')]))
            struct.pack_into('<H', raw, 14, 3)
            with self.assertRaisesRegex(project.InputError, 'parameter length'):
                events.decode_record(bytes(raw), 'condition', 0, 0)
            with self.assertRaisesRegex(project.InputError, 'trailing record bytes'):
                events.decode_record(record('condition', -1, opcode, 0, []) + b'x', 'condition', 0, 0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ConstantConditionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_global_readable_reconstruction_and_immutable_bundle(self):
        program = row([record('condition', -1, op, 0, []) for op in (-1, -2, -9)],
                      [record('action', -1, -1, 0, [])]) + bytes(2)
        raw = action_project(program); doc = events.event_document(self.reader, raw)
        self.assertTrue(doc['coverage']['constant_condition_returns'])
        for k in ('opcode_semantics', 'parameter_semantics', 'expression_evaluation', 'global_reference_resolution'):
            self.assertFalse(doc['coverage'][k])
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            records = pr['rows'][0]['records']
            self.assertEqual([r['constant_condition_return']['return_carry'] for r in records[:2]], [True, False])
            for r in records[2:]: self.assertNotIn('constant_condition_return', r)
        self.assertEqual(events.readable(doc).count('CONSTANT_CONDITION_RETURN '), 10)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            path = bundle.save_bundle(manifest, files, Path(scratch))
            old = {p.name: p.read_bytes() for p in path.iterdir()}
            self.assertEqual(bundle.save_bundle(manifest, files, Path(scratch)), path)
            changed = dict(files); changed['events.json'] += b' '
            with self.assertRaises(project.InputError): bundle.save_bundle(manifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, old)

    def test_late_invalid_unused_expression_refused_before_output_or_report(self):
        payload = expression([token(255, struct.pack('<i', 123456))])
        raw = action_project(row([record('condition', -1, -1, 0, [(22, payload)])], []) + bytes(2))
        at = raw.rfind(token(255, struct.pack('<i', 123456)))
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
    def test_original_independent_source_walk(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes(); game = self.reader.read(raw); programs = []
        for level in game.levels():
            for block in self.reader.level_blocks(level.data)[1]:
                if block.data and block.ident == 4: programs.append(('frame', block.data[10:]))
        for segment in game.segments:
            if segment.ident == 3 and segment.data:
                start, size = struct.unpack_from('<II', segment.data, 12)
                programs.append(('global', segment.data[start:start + size]))
        observed = []; counts = collections.Counter(); total = 0
        for scope, data in programs:
            at = 0
            while (size := abs(struct.unpack_from('<h', data, at)[0])):
                nc, na = data[at + 2:at + 4]; rec = at + 14
                for i in range(nc + na):
                    extent = struct.unpack_from('<H', data, rec)[0]; total += 1
                    kind, opcode = struct.unpack_from('<bb', data, rec + 2)
                    if i < nc and kind == -1 and opcode in (-1, -2):
                        observed.append((opcode, data[rec:rec + 14].hex(), opcode == -1))
                        counts[(scope, opcode)] += 1
                        self.assertEqual(data[rec + 10], 0)
                    rec += extent
                self.assertEqual(rec, at + size); at += size
        doc = events.event_document(self.reader, raw); exported = []
        for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            for row_ in pr['rows']:
                for rec in row_['records']:
                    if 'constant_condition_return' in rec:
                        v = rec['constant_condition_return']
                        exported.append((rec['opcode'], rec['header_hex'], v['return_carry']))
                        self.assertFalse(v['runtime_resolution']); self.assertIsNone(v['condition_result'])
        self.assertEqual(exported, observed); self.assertEqual(total, 9306)
        self.assertEqual(len(observed), 6)
        self.assertEqual(counts, {('frame', -1): 1, ('global', -1): 5})
