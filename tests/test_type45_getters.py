import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import expression, token, expression_program, reconstruct_expression
from test_event_positions import position_project


def getter(items, prefix=0, suffix=b''):
    return events.decode_type45_getter(events.decode_expression(expression(items, prefix, suffix)))


def literal(value):
    return token(255, struct.pack('<i', value))


class Type45GetterTests(unittest.TestCase):
    def test_all_prefix_words_ignored_lone_string_pointer_tag_and_no_encoding_guess(self):
        for prefix in range(65536):
            out = getter([token(0x3FF, b'\xfftext\0opaque')], prefix, b'kept')
            ret = out['conditional_lone_string_return']
            self.assertEqual((ret['parameter_relative_offset'], ret['bytes_hex']), (10, b'\xfftext'.hex()))
            self.assertEqual((ret['dx_raw_u16'], ret['bx_raw_u16'], ret['carry']), (1, 0, False))
            self.assertEqual(ret['eax'], 'runtime_parameter_address_unknown')
            self.assertEqual(ret['source_encoding'], 'unknown')
            self.assertFalse(out['stored_prefix_read_by_getter'])
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(out['caller_interpretation'], 'unknown')
            self.assertNotIn('filename', out)
            self.assertNotIn('eax_raw_u32', ret)

    def test_empty_string_bounded_nul_tails_and_large_extent_preserved(self):
        for value in (b'', b'a', b'\xff\x80\xe4', b'line\n"quote"\\', b'a' * 65521):
            payload = expression([token(0x3FF, value + b'\0\xfftail')], suffix=b'\xffsuffix')
            out = events.decode_expression(payload)
            ret = events.decode_type45_getter(out)['conditional_lone_string_return']
            self.assertEqual(ret['bytes_hex'], value.hex())
            self.assertEqual(out['tokens'][0]['string_literal']['suffix_hex'], b'\xfftail'.hex())
            self.assertEqual(out['suffix_hex'], b'\xffsuffix'.hex())
            self.assertEqual(reconstruct_expression(out), payload)
            if len(payload) < 1000:
                for rec in events.decode_rows(expression_program(payload, 45))[0]['records']:
                    self.assertEqual(rec['parameters'][0]['payload_hex'], payload.hex())

    def test_closed_integer_returns_and_cpu_fault_have_no_string_pointer(self):
        for items, expected in [([literal(-7)], 0xFFFFFFF9),
                                ([literal(2147483647), token(0x200), literal(1)], 0x80000000),
                                ([literal(-7), token(0x800), literal(3)], 0xFFFFFFFE),
                                ([literal(-7), token(0x800), literal(0)], 0),
                                ([token(0xFFFF), literal(7), token(0x200), literal(3), token(0xFDFF), token(0x600), literal(5)], 50)]:
            out = getter(items, 65535)
            self.assertEqual(out['conditional_closed_integer_return'], {
                'status': 'value', 'eax_raw_u32': expected, 'dx_raw_u16': 0, 'bx_raw_u16': 0, 'carry': False})
            self.assertEqual(out['conditional_lone_string_return'], {'status': 'unsupported_shape'})
        for op in (0x800, 0xA00):
            out = getter([literal(-2147483648), token(op), literal(-1)])
            self.assertEqual(out['conditional_closed_integer_return'], {
                'status': 'cpu_exception', 'fault': 'x86_divide_error', 'vector': 0, 'exception_recovery': 'unknown'})
            self.assertNotIn('carry', out['conditional_closed_integer_return'])

    def test_compound_recursive_dynamic_and_empty_strings_never_resolved(self):
        for items in ([], [token(0x1FF)], [token(0xFFFF), token(0x3FF, b'x\0'), token(0xFDFF)],
                      [token(0x3FF, b'x\0'), token(0x200), token(0x3FF, b'y\0')],
                      [token(0x3FF, b'x\0'), token(0x1FF)]):
            out = getter(items)
            self.assertEqual(out['conditional_lone_string_return'], {'status': 'unsupported_shape'})
            self.assertNotIn('eax_raw_u32', out['conditional_closed_integer_return'])
            self.assertFalse(out['runtime_resolution'])

    def test_exact_type45_both_roles_prior_views_unchanged_and_malformed_refused(self):
        payload = expression([token(0x3FF, b'x\0')], 0x8001, b'kept')
        for kind in [*events.EXPRESSION_TYPES, 46, 48, 999]:
            source = expression_program(payload, kind)
            rows = events.decode_rows(source)
            self.assertEqual(reconstruct_program({'rows': rows}), source)
            for rec in rows[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('type45_getter_storage' in q, kind == 45)
                self.assertEqual('expression_getter_storage' in q, kind == 22)
                self.assertEqual(q['meaning'], 'unknown')
                self.assertEqual(q['payload_hex'], payload.hex())
        for payload in (bytes(3), expression([token(0x3FF, b'no NUL')]), b'\0\0\xff\x03\x01\0'):
            with self.assertRaises(project.InputError):
                events.decode_rows(expression_program(payload, 45))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class Type45GetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_roles_scopes_readable_and_false_general_coverage(self):
        raw, source = position_project([(45, expression([token(0x3FF, b'\xffx\0')], 65535))])
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type45_expression_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation', 'global_reference_resolution'):
            self.assertFalse(d['coverage'][key])
        count = 0
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), source)
            for rec in pr['rows'][0]['records']:
                g = rec['parameters'][0]['type45_getter_storage']
                self.assertEqual(g['conditional_lone_string_return']['bytes_hex'], 'ff78')
                self.assertFalse(g['runtime_resolution']); count += 1
        self.assertEqual(count, 10)
        self.assertEqual(events.readable(d).count('TYPE45_GETTER '), count)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_repeat_and_immutable_refusal(self):
        raw, _ = position_project([(45, expression([token(0x3FF, b'x\0')]))])
        d = events.event_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(d))
        self.assertEqual(files['events.txt'], events.readable(d).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            old = {p.name: p.read_bytes() for p in target.iterdir()}
            bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)
            changed = copy.deepcopy(files); changed['events.txt'] += b'changed'
            updated = json.loads(changed['manifest.json'])
            for component in updated['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(updated)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(updated, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_missing_string_nul_refused_before_output_or_reporting(self):
        raw, _ = position_project([(45, expression([token(0x3FF, b'unique\0')]))])
        at = raw.rfind(b'unique\0'); self.assertGreater(at, 0)
        bad = raw[:at] + b'uniqueX' + raw[at + 7:]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as savebundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); savebundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_source_strings_roles_and_lossless_programs(self):
        from collections import Counter
        path = Path(os.environ['FF_TEST_PROJECT']); raw = path.read_bytes()
        d = events.event_document(self.reader, raw); game = self.reader.read(raw)
        programs = []
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((p, blocks[p['block_id']].data, 'frame') for p in f['programs'])
        programs.extend((p, game.segments[p['segment_id']].data, 'global') for p in d['global_events'])
        roles, scopes = Counter(), Counter()
        for pr, block, scope in programs:
            data = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), data)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] != 45:
                            self.assertNotIn('type45_getter_storage', q); continue
                        at = q['offset']; size = int.from_bytes(data[at:at+2], 'little')
                        self.assertEqual(data[at+4:at+10], b'\0\0\xff\x03\x12\0')
                        self.assertEqual(data[at+24:at+size], bytes(2))
                        literal = data[at+10:at+24].split(b'\0', 1)[0]
                        g = q['type45_getter_storage']; ret = g['conditional_lone_string_return']
                        self.assertEqual((ret['bytes_hex'], ret['parameter_relative_offset'], ret['dx_raw_u16']), (literal.hex(), 10, 1))
                        self.assertFalse(g['runtime_resolution'])
                        self.assertEqual(g['conditional_closed_integer_return'], {'status': 'unsupported_tokens'})
                        roles[rec['role']] += 1; scopes[scope] += 1
        self.assertEqual(dict(roles), {'action': 5, 'condition': 2})
        self.assertEqual(dict(scopes), {'frame': 7})
        self.assertEqual(path.read_bytes(), raw)
