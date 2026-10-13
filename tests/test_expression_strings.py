import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression


class StringLiteralTests(unittest.TestCase):
    def test_byte_values_empty_high_bytes_escapes_and_opaque_tail(self):
        for value in (b'', b'./settings.ini', b'\xff\x80\xe4', b'line\n"quote"\\', b'a' * 65530):
            raw = expression([token(0x3FF, value + b'\0')], prefix=0xBEEF, suffix=b'\xffopaque')
            out = events.decode_expression(raw)
            literal = out['tokens'][0]['string_literal']
            self.assertEqual(literal, {'token_offset': 4, 'bytes_hex': value.hex(),
                                      'byte_view_latin1': value.decode('latin1'),
                                      'terminator_token_offset': 4 + len(value), 'suffix_hex': '',
                                      'source_encoding': 'unknown', 'evidence': 'cnc_runtime_dispatch'})
            self.assertEqual(reconstruct_expression(out), raw)
            self.assertEqual(out['tokens'][0]['meaning'], 'unknown')
            self.assertIsNone(out['tokens'][0]['object_reference_annotation'])
        out = events.decode_expression(expression([token(0x3FF, b'x\0hidden\0\xff')]))
        self.assertEqual(out['tokens'][0]['string_literal']['bytes_hex'], '78')
        self.assertEqual(out['tokens'][0]['string_literal']['suffix_hex'], b'hidden\0\xff'.hex())

    def test_missing_terminator_cannot_borrow_next_token_or_expression_terminator(self):
        for payload in (b'', b'x', b'abc', b'\xff' * 32):
            with self.subTest(payload=payload), self.assertRaises(project.InputError):
                events.decode_expression(expression([token(0x3FF, payload), token(0xFF, bytes(4))]))

    def test_exact_code_mixed_tokens_and_no_expression_evaluation(self):
        items = [token(0x3FF, b'a\0'), token(0x200), token(0xFF, struct.pack('<i', -7)),
                 token(0x1FF), token(0xFFFF), token(0xFEFF), token(0x4FF)]
        raw = expression(items, suffix=token(0x3FF, b'ignored\0'))
        out = events.decode_expression(raw)
        self.assertEqual(reconstruct_expression(out), raw)
        self.assertEqual([i for i, t in enumerate(out['tokens']) if 'string_literal' in t], [0])
        self.assertEqual(out['tokens'][2]['integer_literal']['value_signed_i32'], -7)
        self.assertNotIn('value', out)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class StringLiteralContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_roles_all_parameter_types_frame_global_and_escaped_text(self):
        value = b'\xff\n"own"\\'
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, program = expression_project(expression([token(0x3FF, value + b'\0tail')]))
            size = 4 + len(expression([token(0x3FF, value + b'\0tail')]))
            raw = raw.replace(struct.pack('<HH', size, 22), struct.pack('<HH', size, kind))
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['expression_string_literals'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            for p in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                for rec in p['rows'][0]['records']:
                    q = rec['parameters'][0]
                    self.assertEqual(q['type'], kind)
                    self.assertEqual(q['expression_storage']['tokens'][0]['string_literal']['bytes_hex'], value.hex())
            text = events.readable(doc)
            self.assertEqual(text.count('"byte_view_latin1": "\\u00ff\\n\\"own\\"\\\\"'), 10)
            self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_late_unterminated_literal_refuses_all_outputs_and_reporting(self):
        raw, _ = expression_project(expression([token(0x3FF, b'own\0')]))
        at = raw.rfind(token(0x3FF, b'own\0'))
        bad = raw[:at + 7] + b'x' + raw[at + 8:]
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

    def test_lossless_program_and_immutable_bundle_repeat(self):
        raw, program = expression_project(expression([token(0x3FF, b'a\0opaque\xff'), token(0x200),
                                                      token(0x3FF, b'b\0')]))
        doc = events.event_document(self.reader, raw)
        for p in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            self.assertEqual(reconstruct_program(p), program)
        manifest, files = export_project.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            path = export_project.save_bundle(manifest, files, Path(scratch))
            first = {p.name: p.read_bytes() for p in path.iterdir()}
            export_project.save_bundle(*export_project.research_bundle(self.reader, raw), Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, first)

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_source_bytes_external_walk_and_lossless_programs(self):
        from klikback.core.common.event_object_registry import expression_object_slots
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        doc = events.event_document(self.reader, raw)
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
        count = 0
        for p, data in programs:
            self.assertEqual(reconstruct_program(p), data)
            for row in p['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in events.EXPRESSION_TYPES:
                            continue
                        end = q['offset'] + q['bytes']
                        list(expression_object_slots(data, q['offset'], end))
                        cursor = q['offset'] + 6
                        observed = []
                        while int.from_bytes(data[cursor:cursor + 2], 'little'):
                            code, size = struct.unpack_from('<HH', data, cursor)
                            if code == 0x3FF:
                                field = data[cursor + 4:cursor + size]
                                value, sep, tail = field.partition(b'\0')
                                self.assertEqual(sep, b'\0')
                                observed.append((value.hex(), tail.hex(), 4 + len(value)))
                                count += 1
                            cursor += size
                        self.assertEqual([(t['string_literal']['bytes_hex'], t['string_literal']['suffix_hex'],
                                           t['string_literal']['terminator_token_offset'])
                                          for t in q['expression_storage']['tokens'] if 'string_literal' in t], observed)
        self.assertEqual(count, 7)
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
