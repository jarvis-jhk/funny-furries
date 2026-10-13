import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


class ControlTests(unittest.TestCase):
    def test_recursive_operand_and_two_unconsumed_stops_preserve_storage(self):
        items = [token(0xFFFF), token(0xFF, struct.pack('<i', -7)), token(0xFDFF),
                 token(0x200), token(0xFF, struct.pack('<i', 3)), token(0xFEFF)]
        raw = expression(items, prefix=0xBEEF, suffix=token(0xFFFF) + b'opaque')
        out = events.decode_expression(raw)
        self.assertEqual(reconstruct_expression(out), raw)
        self.assertEqual(out['tokens'][0]['expression_control'], {
            'operation': 'recursive_operand', 'inner_start_token_offset': 4,
            'inner_return_cursor': 'unconsumed_evaluator_stop',
            'dispatch_return_cursor': 'after_stop_token', 'delimiter_pairing': 'unknown',
            'other_operand_tags': 'unknown', 'evidence': 'cnc_runtime_dispatch'})
        for index in (2, 5):
            self.assertEqual(out['tokens'][index]['expression_control'], {
                'operation': 'evaluator_stop', 'return_cursor': 'unconsumed',
                'delimiter_role': 'unknown', 'evidence': 'cnc_runtime_evaluator'})
        self.assertTrue(all(t['meaning'] == 'unknown' for t in out['tokens']))
        self.assertTrue(all(t['object_reference_annotation'] is None for t in out['tokens']))
        self.assertNotIn('value', out)
        self.assertNotIn('result', out)

    def test_nested_unbalanced_and_mixed_contexts_never_invent_pairing_or_results(self):
        fixtures = [[token(0xFFFF)], [token(0xFEFF), token(0xFDFF)],
                    [token(0xFFFF)] * 32 + [token(0xFF, struct.pack('<i', -2147483648))]
                    + [token(0xFEFF)] * 32,
                    [token(0xFFFF), token(0x3FF, b'x\0'), token(0xFDFF),
                     token(0xA02, struct.pack('<HH', 7, 9)), token(0x800), token(0xFEFF)]]
        for items in fixtures:
            raw = expression(items)
            out = events.decode_expression(raw)
            self.assertEqual(reconstruct_expression(out), raw)
            self.assertNotIn('pairing', out)
            self.assertNotIn('result', out)
            self.assertNotIn('grammar_valid', out)
            self.assertEqual([t['raw_hex'] for t in out['tokens']], [i.hex() for i in items])
            for t in out['tokens']:
                if t['code_raw_u16'] in (0xFFFF, 0xFEFF, 0xFDFF):
                    self.assertIn('expression_control', t)
                    self.assertNotIn('integer_operation', t)
                    self.assertNotIn('integer_prefix_operation', t)
                    self.assertNotIn('pair_id', t['expression_control'])

    def test_unsupported_control_extents_fail_neighbor_codes_remain_opaque(self):
        for code in (0xFFFF, 0xFEFF, 0xFDFF):
            for size in range(5, 15):
                with self.subTest(code=code, size=size), self.assertRaises(project.InputError):
                    events.decode_expression(expression([token(code, bytes(size - 4))]))
            for size in range(4):
                with self.subTest(code=code, size=size), self.assertRaises(project.InputError):
                    events.decode_expression(expression([struct.pack('<HH', code, size)]))
        for code in (0xFFFE, 0xFCFF, 0xFFFF - 0x1000):
            out = events.decode_expression(expression([token(code, b'opaque')]))
            self.assertNotIn('expression_control', out['tokens'][0])

    def test_structural_scan_continues_after_runtime_stop_but_not_storage_terminator(self):
        raw = expression([token(0xFEFF), token(0xFF, struct.pack('<i', 17)), token(0xFFFF)],
                         suffix=token(0xFDFF) + token(0xFFFF))
        out = events.decode_expression(raw)
        self.assertEqual([t['code_raw_u16'] for t in out['tokens']], [0xFEFF, 0xFF, 0xFFFF])
        self.assertEqual(out['tokens'][1]['integer_literal']['value_signed_i32'], 17)
        self.assertEqual(out['suffix_hex'], (token(0xFDFF) + token(0xFFFF)).hex())
        self.assertEqual(reconstruct_expression(out), raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ControlContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_roles_all_expression_types_scopes_and_readable_annotations(self):
        payload = expression([token(0xFFFF), token(0xFF, bytes(4)), token(0xFEFF), token(0xFDFF)])
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, _ = expression_project(payload)
            raw = raw.replace(struct.pack('<HH', len(payload) + 4, 22),
                              struct.pack('<HH', len(payload) + 4, kind))
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_control_tokens'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            for program in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                for rec in program['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['type'], kind)
                    ts = q['expression_storage']['tokens']
                    self.assertEqual(ts[0]['expression_control']['operation'], 'recursive_operand')
                    self.assertEqual(ts[2]['expression_control']['operation'], 'evaluator_stop')
            text = events.readable(doc)
            self.assertEqual(text.count('"operation": "recursive_operand"'), 10)
            self.assertEqual(text.count('"operation": "evaluator_stop"'), 20)
            self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_late_invalid_control_refuses_every_output_and_fault_report(self):
        for code in (0xFFFF, 0xFEFF, 0xFDFF):
            raw, _ = expression_project(expression([token(code)]))
            at = raw.rfind(token(code))
            raw = raw[:at + 2] + struct.pack('<H', 5) + raw[at + 4:]
            for module, flags in [(events, []), (events, ['--text']), (export_project, [])]:
                with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                        patch.object(project, 'load_reader', return_value=self.reader), \
                        patch.object(Path, 'read_bytes', return_value=raw), \
                        patch.object(project, 'save_export') as save, \
                        patch.object(export_project, 'save_bundle') as bundle, \
                        patch.object(project, 'report_fault') as report:
                    self.assertEqual(module.main(), 2)
                    save.assert_not_called()
                    bundle.assert_not_called()
                    report.assert_not_called()

    def test_bundle_and_program_lossless_with_unbalanced_markers_immutable_repeat(self):
        payload = expression([token(0xFFFF), token(0x3FF, b'a\0'), token(0xFDFF), token(0xFFFF)])
        raw, program = expression_project(payload)
        doc = events.event_document(self.reader, raw)
        manifest, files = export_project.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        for p in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(p), program)
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            target = export_project.save_bundle(manifest, files, Path(scratch))
            first = {p.name: p.read_bytes() for p in target.iterdir()}
            export_project.save_bundle(*export_project.research_bundle(self.reader, raw), Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, first)

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_walk_control_words_extents_and_lossless_programs(self):
        from klikback.core.common.event_object_registry import expression_object_slots
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        doc = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        programs = []
        for frame, level in zip(doc['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for p in frame['programs']:
                data = blocks[p['block_id']].data
                programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        for p in doc['global_events']:
            data = game.segments[p['segment_id']].data
            programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        count = {0xFFFF: 0, 0xFEFF: 0, 0xFDFF: 0}
        for p, data in programs:
            self.assertEqual(reconstruct_program(p), data)
            for row in p['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in (15, 22, 23, 45, 52, 53):
                            continue
                        list(expression_object_slots(data, q['offset'], q['offset'] + q['bytes']))
                        cursor = q['offset'] + 6
                        observed = []
                        while int.from_bytes(data[cursor:cursor + 2], 'little'):
                            code = int.from_bytes(data[cursor:cursor + 2], 'little')
                            size = int.from_bytes(data[cursor + 2:cursor + 4], 'little')
                            if code in count:
                                self.assertEqual(size, 4)
                                observed.append((cursor - (q['offset'] + 4), code, data[cursor:cursor + size].hex()))
                                count[code] += 1
                            cursor += size
                        annotated = [t for t in q['expression_storage']['tokens'] if 'expression_control' in t]
                        self.assertEqual([(t['payload_offset'], t['code_raw_u16'], t['raw_hex']) for t in annotated], observed)
                        for t in annotated:
                            expected = 'recursive_operand' if t['code_raw_u16'] == 65535 else 'evaluator_stop'
                            self.assertEqual(t['expression_control']['operation'], expected)
        self.assertEqual(count, {0xFFFF: 4, 0xFEFF: 105, 0xFDFF: 17})
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
