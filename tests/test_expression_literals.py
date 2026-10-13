import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


class LiteralTests(unittest.TestCase):
    def test_signed_boundaries_nonzero_prefix_suffix_and_lossless_bytes(self):
        for value in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
            raw = expression([token(0xFF, struct.pack('<i', value))], prefix=0xBEEF, suffix=b'\xffown\0tail')
            out = events.decode_expression(raw)
            self.assertEqual(reconstruct_expression(out), raw)
            self.assertEqual(out['tokens'][0]['integer_literal'], {
                'token_offset': 4, 'value_signed_i32': value,
                'value_raw_u32': value & 0xFFFFFFFF, 'evidence': 'cnc_runtime_dispatch'})
            self.assertEqual(out['tokens'][0]['meaning'], 'unknown')
            self.assertIsNone(out['tokens'][0]['object_reference_annotation'])

    def test_mixed_tokens_no_operator_evaluation_no_modern_code_alias(self):
        items = [token(0x400), token(0xFF, struct.pack('<i', -123)), token(0x200),
                 token(0xFF, struct.pack('<i', 7654321)), token(0xFFFF), token(0x1FF),
                 token(0x3002, struct.pack('<HH', 0, 7)), token(0xFEFF)]
        raw = expression(items, suffix=token(0xFF, struct.pack('<i', 999)))
        out = events.decode_expression(raw)
        self.assertEqual(reconstruct_expression(out), raw)
        self.assertEqual([t['integer_literal']['value_signed_i32'] for t in out['tokens']
                          if 'integer_literal' in t], [-123, 7654321])
        self.assertEqual([i for i, t in enumerate(out['tokens']) if 'integer_literal' in t], [1, 3])
        self.assertNotIn('value', out)
        self.assertNotIn('integer_literal', out['tokens'][4])
        self.assertEqual(out['tokens'][6]['object_reference_annotation']['reference_raw_u16'], 0)

    def test_literal_extent_refused_without_rejecting_unknown_shapes(self):
        for size in (*range(4, 8), *range(9, 14)):
            with self.subTest(size=size), self.assertRaises(project.InputError):
                events.decode_expression(expression([token(0xFF, bytes(size - 4))]))
        for code in (0x1FF, 0xFFFF, 0xFEFF, 0x0200):
            out = events.decode_expression(expression([token(code)]))
            self.assertNotIn('integer_literal', out['tokens'][0])


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class LiteralContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_roles_all_expression_types_global_and_frame_readable_values(self):
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, _ = expression_project(expression([token(0xFF, struct.pack('<i', -16777217))]))
            # Substitute the parameter type throughout this synthetic container.
            old = struct.pack('<HH', 16, 22)
            raw = raw.replace(old, struct.pack('<HH', 16, kind))
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_integer_literals'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
            for program in programs:
                for rec in program['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['type'], kind)
                    self.assertEqual(q['expression_storage']['tokens'][0]['integer_literal']['value_signed_i32'],
                                     -16777217)
            text = events.readable(doc)
            self.assertEqual(text.count('"value_signed_i32": -16777217'), 10)
            self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_late_invalid_literal_refuses_all_outputs_without_fault_report(self):
        raw, _ = expression_project(expression([token(0xFF, bytes(4))]))
        at = raw.rfind(token(0xFF, bytes(4)))
        bad = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in [(events, []), (events, ['--text']), (export_project, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(export_project, 'save_bundle') as bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called()
                bundle.assert_not_called()
                report.assert_not_called()

    def test_bundle_values_repeat_and_mixed_expression_preservation(self):
        payload = expression([token(0xFF, struct.pack('<i', -256)), token(0x200),
                              token(0xFF, struct.pack('<i', 17))])
        raw, program = expression_project(payload)
        manifest, files = export_project.research_bundle(self.reader, raw)
        doc = events.event_document(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        for p in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(p), program)
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            path = export_project.save_bundle(manifest, files, Path(scratch))
            first = {p.name: p.read_bytes() for p in path.iterdir()}
            export_project.save_bundle(*export_project.research_bundle(self.reader, raw), Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, first)

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_source_values_external_token_walk_and_lossless_programs(self):
        from klikback.core.common.event_object_registry import expression_object_slots
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        doc = events.event_document(self.reader, raw)
        count = 0
        negative = 0
        programs = []
        game = self.reader.read(raw)
        for frame, level in zip(doc['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for p in frame['programs']:
                data = blocks[p['block_id']].data
                programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        for p in doc['global_events']:
            data = game.segments[p['segment_id']].data
            programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        for p, data in programs:
            self.assertEqual(reconstruct_program(p), data)
            for row in p['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in (15, 22, 23, 45, 52, 53):
                            continue
                        payload_at = q['offset'] + 4
                        end = q['offset'] + q['bytes']
                        # Execute the independent reader's complete token walk;
                        # literal values then come directly from source bytes.
                        list(expression_object_slots(data, q['offset'], end))
                        cursor = payload_at + 2
                        observed = []
                        while int.from_bytes(data[cursor:cursor + 2], 'little'):
                            code = int.from_bytes(data[cursor:cursor + 2], 'little')
                            size = int.from_bytes(data[cursor + 2:cursor + 4], 'little')
                            if code == 255:
                                self.assertEqual(size, 8)
                                value = int.from_bytes(data[cursor + 4:cursor + 8], 'little', signed=True)
                                observed.append(value)
                                count += 1
                                negative += value < 0
                            cursor += size
                        self.assertEqual([t['integer_literal']['value_signed_i32']
                                          for t in q['expression_storage']['tokens'] if 'integer_literal' in t], observed)
        self.assertEqual(count, 3776)
        self.assertGreater(negative, 0)
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
