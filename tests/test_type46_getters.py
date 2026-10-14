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


def literal(value):
    return token(255, struct.pack('<i', value))


def getter(items, prefix=0, suffix=b''):
    return events.decode_type46_getter(events.decode_expression(expression(items, prefix, suffix)))


class Type46GetterTests(unittest.TestCase):
    def test_all_prefixes_ignored_and_lone_byte_string_address_contract(self):
        for prefix in range(65536):
            out = getter([token(0x3FF, b'\xffx\0tail')], prefix, b'suffix')
            ret = out['conditional_lone_string_return']
            self.assertEqual(ret, {
                'status': 'parameter_byte_string_address', 'eax': 'runtime_parameter_address_unknown',
                'parameter_relative_offset': 10, 'address_arithmetic_bits': 32,
                'address_overflow': 'wrap_modulo_2_to_32', 'bytes_hex': 'ff78',
                'dx_raw_u16': 1, 'bx_raw_u16': 0, 'carry': False, 'source_encoding': 'unknown'})
            self.assertFalse(out['stored_prefix_read_by_getter'])
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(out['caller_interpretation'], 'unknown')
            self.assertEqual(out['evidence'], 'cnc_type46_expression_parameter_getter')
            self.assertEqual(out['conditional_normal_return']['assumption'],
                             'type46_dispatch_and_expression_normal_return')
            self.assertEqual((out['first_token_parameter_offset'], out['first_token_payload_offset']), (6, 2))

    def test_byte_boundaries_tails_and_raw_token_reconstruction(self):
        for value in (b'', b'a', b'\x80\xe4\xff', b'line\n"quote"\\', b'a' * 65521):
            payload = expression([token(0x3FF, value + b'\0tail')], 0xFFFF, b'\xffsuffix')
            parsed = events.decode_expression(payload)
            self.assertEqual(reconstruct_expression(parsed), payload)
            self.assertEqual(events.decode_type46_getter(parsed)['conditional_lone_string_return']['bytes_hex'], value.hex())
            self.assertEqual(parsed['tokens'][0]['string_literal']['suffix_hex'], b'tail'.hex())
            if len(payload) < 1000:
                rows = events.decode_rows(expression_program(payload, 46))
                self.assertEqual(reconstruct_program({'rows': rows}), expression_program(payload, 46))

    def test_integer_recursive_wrap_and_fault_returns_remain_conditional(self):
        for items, expected in [([literal(-7)], 0xFFFFFFF9),
                                ([literal(2147483647), token(0x200), literal(1)], 0x80000000),
                                ([literal(-7), token(0x800), literal(3)], 0xFFFFFFFE),
                                ([literal(7), token(0x800), literal(0)], 0),
                                ([literal(-7), token(0xA00), literal(0)], 0xFFFFFFF9),
                                ([token(0xFFFF), literal(7), token(0x200), literal(3), token(0xFDFF), token(0x600), literal(5)], 50)]:
            out = getter(items, 0x8000)
            self.assertEqual(out['conditional_closed_integer_return'], {
                'status': 'value', 'eax_raw_u32': expected, 'dx_raw_u16': 0, 'bx_raw_u16': 0, 'carry': False})
            self.assertEqual(out['conditional_lone_string_return'], {'status': 'unsupported_shape'})
        for code in (0x800, 0xA00):
            out = getter([literal(-2147483648), token(code), literal(-1)])
            self.assertEqual(out['conditional_closed_integer_return'], {
                'status': 'cpu_exception', 'fault': 'x86_divide_error', 'vector': 0, 'exception_recovery': 'unknown'})

    def test_unknown_dynamic_empty_and_compound_strings_have_no_resolved_return(self):
        for items in ([], [token(0x1FF)], [token(0xFFFF), token(0x3FF, b'x\0'), token(0xFDFF)],
                      [token(0x3FF, b'x\0'), token(0x200), token(0x3FF, b'y\0')]):
            out = getter(items)
            self.assertEqual(out['conditional_lone_string_return'], {'status': 'unsupported_shape'})
            self.assertNotIn('eax_raw_u32', out['conditional_closed_integer_return'])
            self.assertFalse(out['runtime_resolution'])

    def test_exact_type_both_roles_and_strict_storage_validation(self):
        payload = expression([literal(3)])
        for kind in (22, 23, 45, 46, 47, 48, 52, 53, 999):
            rows = events.decode_rows(expression_program(payload, kind))
            for rec in rows[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('type46_getter_storage' in q, kind == 46)
                self.assertEqual('type45_getter_storage' in q, kind == 45)
                self.assertEqual(q['payload_hex'], payload.hex())
                self.assertEqual(q['meaning'], 'unknown')
        for payload in (b'', bytes(3), expression([token(0x3FF, b'no NUL')]),
                        bytes(2) + struct.pack('<HH', 255, 65535),
                        bytes(2) + literal(1), expression([token(0x3FF, b'x\0')])[:-2]):
            with self.subTest(payload=payload.hex()), self.assertRaises(project.InputError):
                events.decode_rows(expression_program(payload, 46))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class Type46GetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_roles_scopes_text_and_dynamic_reference_candidates_without_resolution(self):
        payload = expression([token(0x0002, bytes(4))])
        raw, program = position_project([(46, payload)])
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type46_expression_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation', 'global_reference_resolution'):
            self.assertFalse(d['coverage'][key])
        count = 0
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                self.assertEqual(reconstruct_expression(q['expression_storage']), payload)
                self.assertEqual(q['type46_getter_storage']['conditional_closed_integer_return'], {'status': 'unsupported_tokens'})
                self.assertFalse(q['type46_getter_storage']['runtime_resolution'])
                self.assertIsNotNone(q['expression_storage']['tokens'][0]['object_reference_annotation'])
                count += 1
        self.assertEqual(count, 10)
        for rec in d['global_events'][0]['rows'][0]['records']:
            ref = rec['parameters'][0]['expression_storage']['tokens'][0]['object_reference_annotation']
            self.assertEqual(ref['status'], 'frame_context_unresolved')
            self.assertEqual(ref['candidates'], [])
        self.assertEqual(events.readable(d).count('TYPE46_GETTER '), count)

    def test_bundle_standalone_repeats_and_immutable_refusal(self):
        raw, _ = position_project([(46, expression([token(0x3FF, b'x\0')]))])
        d = events.event_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(d))
        self.assertEqual(files['events.txt'], events.readable(d).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            old = {p.name: p.read_bytes() for p in target.iterdir()}
            bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch))
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

    def test_late_type46_malformed_expression_refused_before_output_or_reporting(self):
        raw, _ = position_project([(46, expression([token(0x3FF, b'unique\0')]))])
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
    def test_original_independent_source_traversal_confirms_type46_absent(self):
        path = Path(os.environ['FF_TEST_PROJECT']); raw = path.read_bytes()
        d = events.event_document(self.reader, raw); game = self.reader.read(raw)
        programs = []
        for frame, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((pr, blocks[pr['block_id']].data) for pr in frame['programs'])
        programs.extend((pr, game.segments[pr['segment_id']].data) for pr in d['global_events'])
        count = 0
        for pr, block in programs:
            source = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), source)
            at = 0
            while True:
                extent = abs(struct.unpack_from('<h', source, at)[0])
                if not extent:
                    break
                nc, na = source[at + 2:at + 4]; cur = at + 14
                for i in range(nc + na):
                    size = struct.unpack_from('<H', source, cur)[0]; pos = cur + (14 if i < nc else 12)
                    for _ in range(source[cur + 10]):
                        length, kind = struct.unpack_from('<HH', source, pos)
                        self.assertNotEqual(kind, 46); count += 1; pos += length
                    self.assertEqual(pos, cur + size); cur += size
                self.assertEqual(cur, at + extent); at += extent
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        self.assertNotIn('type46_getter_storage', q)
        self.assertEqual(count, 8160)
        self.assertEqual(path.read_bytes(), raw)
