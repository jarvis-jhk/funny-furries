import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


class AdditionTests(unittest.TestCase):
    def test_exact_code_numeric_path_only_and_lossless_storage(self):
        raw = expression([token(0xFF, struct.pack('<i', 2147483647)), token(0x200),
                          token(0xFF, struct.pack('<i', 1))], prefix=0xBEEF,
                         suffix=token(0x200) + b'opaque')
        out = events.decode_expression(raw)
        self.assertEqual(reconstruct_expression(out), raw)
        self.assertEqual(out['tokens'][1]['integer_operation'], {
            'name': 'add', 'bits': 32, 'overflow': 'wrap_modulo_2_32',
            'required_operand_tag': 0, 'other_operand_tags': 'unknown',
            'evidence': 'cnc_runtime_operator_table'})
        self.assertEqual(out['tokens'][1]['meaning'], 'unknown')
        self.assertIsNone(out['tokens'][1]['object_reference_annotation'])
        self.assertNotIn('value', out)
        self.assertEqual(out['tokens'][0]['integer_literal']['value_signed_i32'], 2147483647)
        self.assertEqual(out['tokens'][2]['integer_literal']['value_signed_i32'], 1)

    def test_strings_unknown_operands_and_other_operators_do_not_get_evaluated(self):
        items = [token(0x3FF, b'a\0'), token(0x200), token(0x3FF, b'b\0'),
                 token(0x400), token(0x600), token(0x800), token(0xA00),
                 token(0x0202, struct.pack('<HH', 7, 9)), token(0xFFFF), token(0xFEFF)]
        out = events.decode_expression(expression(items))
        self.assertEqual([i for i, t in enumerate(out['tokens']) if t.get('integer_operation', {}).get('name') == 'add'], [1])
        self.assertEqual(out['tokens'][1]['integer_operation']['other_operand_tags'], 'unknown')
        self.assertNotIn('value', out)
        self.assertNotIn('result', out)
        self.assertEqual(reconstruct_expression(out), expression(items))
        # Context cannot be validated as a numeric expression by this storage decoder.
        for items in ([token(0x200)], [token(0x200), token(0x200)],
                      [token(0xFF, bytes(4)), token(0x200)]):
            self.assertEqual(reconstruct_expression(events.decode_expression(expression(items))),
                             expression(items))

    def test_unsupported_operator_extents_refused_other_codes_stay_opaque(self):
        for size in range(5, 15):
            with self.subTest(size=size), self.assertRaises(project.InputError):
                events.decode_expression(expression([token(0x200, bytes(size - 4))]))
        # Short lengths are rejected by the existing token framing guard too.
        for size in range(4):
            with self.subTest(size=size), self.assertRaises(project.InputError):
                events.decode_expression(expression([struct.pack('<HH', 0x200, size)]))
        for code in (0xA00, 0xC00, 0xE00):
            out = events.decode_expression(expression([token(code, b'opaque')]))
            self.assertNotIn('integer_operation', out['tokens'][0])


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class AdditionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_roles_all_expression_types_scopes_and_readable_annotation(self):
        payload = expression([token(0x200)])
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, _ = expression_project(payload)
            raw = raw.replace(struct.pack('<HH', 12, 22), struct.pack('<HH', 12, kind))
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_integer_addition'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
            for program in programs:
                for rec in program['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['type'], kind)
                    self.assertEqual(q['expression_storage']['tokens'][0]['integer_operation']['name'], 'add')
            self.assertEqual(events.readable(doc).count('"name": "add"'), 10)
            self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_late_invalid_operator_refuses_every_output_and_fault_report(self):
        raw, _ = expression_project(expression([token(0x200)]))
        at = raw.rfind(token(0x200))
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

    def test_bundle_mixed_operand_storage_and_immutable_repeat(self):
        payload = expression([token(0x3FF, b'a\0'), token(0x200), token(0xFF, struct.pack('<i', -1))])
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
    def test_original_direct_source_external_walk_and_lossless_programs(self):
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
        count = 0
        for p, data in programs:
            self.assertEqual(reconstruct_program(p), data)
            for row in p['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in (15, 22, 23, 45, 52, 53):
                            continue
                        end = q['offset'] + q['bytes']
                        list(expression_object_slots(data, q['offset'], end))
                        cursor = q['offset'] + 6
                        observed = []
                        while int.from_bytes(data[cursor:cursor + 2], 'little'):
                            code = int.from_bytes(data[cursor:cursor + 2], 'little')
                            size = int.from_bytes(data[cursor + 2:cursor + 4], 'little')
                            if code == 512:
                                self.assertEqual(size, 4)
                                self.assertEqual(data[cursor:cursor + size], b'\0\2\4\0')
                                observed.append(cursor - (q['offset'] + 4))
                                count += 1
                            cursor += size
                        annotated = [t for t in q['expression_storage']['tokens'] if t.get('integer_operation', {}).get('name') == 'add']
                        self.assertEqual([t['payload_offset'] for t in annotated], observed)
                        self.assertTrue(all(t['integer_operation']['name'] == 'add' for t in annotated))
                        self.assertTrue(all(t['integer_operation']['other_operand_tags'] == 'unknown' for t in annotated))
        self.assertEqual(count, 116)
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
