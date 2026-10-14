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
from test_event_expressions import expression, token, expression_program, expression_project


ORIGINAL_FORMS = {"value": 2112, "unsupported_tokens": 349}
ORIGINAL_ROLES = {"action": 2172, "condition": 289}
ORIGINAL_PREFIXES = {0: 2461}

def literal(value):
    return token(255, struct.pack('<i', value))


def getter(items, prefix=0, suffix=b''):
    q = events.decode_rows(expression_program(expression(items, prefix, suffix), 22))[0]['records'][0]['parameters'][0]
    return q['expression_getter_storage']


class ExpressionGetterTests(unittest.TestCase):
    def test_prefix_ignored_numeric_result_tag_bx_carry_and_raw_boundaries(self):
        for value in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
            for prefix in (0, 1, 0x8000, 65535):
                out = getter([literal(value)], prefix, b'opaque\xff')
                self.assertEqual((out['first_token_parameter_offset'], out['first_token_payload_offset']), (6, 2))
                self.assertFalse(out['stored_prefix_read_by_getter'])
                self.assertEqual(out['conditional_closed_integer_return'], {
                    'status': 'value', 'eax_raw_u32': value % 2**32,
                    'dx_raw_u16': 0, 'bx_raw_u16': 0, 'carry': False})
                self.assertFalse(out['runtime_resolution'])
                self.assertEqual(out['caller_interpretation'], 'unknown')
                self.assertEqual(out['conditional_normal_return']['dx'], 'expression_evaluator_tag_not_preserved_incoming_word')

    def test_compound_recursive_wrap_zero_divisor_and_cpu_fault_return_separated(self):
        cases = [([literal(2147483647), token(0x200), literal(1)], 0x80000000),
                 ([literal(-7), token(0x800), literal(3)], 0xFFFFFFFE),
                 ([literal(-7), token(0x800), literal(0)], 0),
                 ([token(0xFFFF), literal(7), token(0x200), literal(3), token(0xFDFF), token(0x600), literal(5)], 50)]
        for items, expected in cases:
            self.assertEqual(getter(items)['conditional_closed_integer_return']['eax_raw_u32'], expected)
        for op in (0x800, 0xA00):
            probe = getter([literal(-2147483648), token(op), literal(-1)])['conditional_closed_integer_return']
            self.assertEqual(probe, {'status': 'cpu_exception', 'fault': 'x86_divide_error', 'vector': 0, 'exception_recovery': 'unknown'})
            self.assertNotIn('carry', probe)
            self.assertNotIn('eax_raw_u32', probe)

    def test_unknown_empty_string_and_dynamic_never_get_a_numeric_return(self):
        for items, status in [([], 'unsupported_shape'), ([token(0x400)], 'unsupported_shape'),
                              ([token(0x3FF, b'text\0')], 'unsupported_tokens'),
                              ([token(0x1FF)], 'unsupported_tokens'),
                              ([literal(-2147483648), token(0x800), literal(-1), token(0x200), token(0x1FF)], 'unsupported_tokens')]:
            self.assertEqual(getter(items)['conditional_closed_integer_return'], {'status': status})

    def test_exact_type22_only_both_roles_and_prior_expression_scalar_comparison_views(self):
        payload = expression([literal(-7)], prefix=0x8001, suffix=b'kept')
        for kind in [*events.EXPRESSION_TYPES, 999]:
            program = expression_program(payload, kind)
            rows = events.decode_rows(program)
            self.assertEqual(reconstruct_program({'rows': rows}), program)
            for rec in rows[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('expression_getter_storage' in q, kind == 22)
                self.assertEqual(q['payload_hex'], payload.hex())
                self.assertEqual(q['meaning'], 'unknown')
                if kind in events.EXPRESSION_TYPES:
                    self.assertEqual(q['expression_storage']['constant_integer_evaluation']['value_signed_i32'], -7)
                    self.assertEqual(q['expression_storage']['suffix_hex'], b'kept'.hex())
                if kind == 15:
                    self.assertEqual(q['scalar_getter_storage']['conditional_getter_return']['eax_raw_u32'], 0x8001)
                if kind == 23:
                    self.assertEqual(q['comparison_prefix_storage']['getter_bx_on_normal_expression_return_raw_u16'], 0x8002)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ExpressionGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_scopes_roles_readable_reconstruction_and_false_general_coverage(self):
        raw, program = expression_project(expression([literal(-7)], prefix=65535))
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type22_expression_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation'):
            self.assertFalse(d['coverage'][key])
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), program)
            for rec in pr['rows'][0]['records']:
                g = rec['parameters'][0]['expression_getter_storage']
                self.assertFalse(g['runtime_resolution'])
                self.assertEqual(g['conditional_closed_integer_return']['eax_raw_u32'], 0xFFFFFFF9)
        self.assertEqual(events.readable(d).count('EXPRESSION_GETTER '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw, _ = expression_project(expression([literal(-17)], prefix=65535))
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
            changed = copy.deepcopy(files)
            changed['events.txt'] += b'changed'
            newmanifest = json.loads(changed['manifest.json'])
            for component in newmanifest['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(newmanifest)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(newmanifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_malformed_expression_refused_before_output_or_reporting(self):
        raw, _ = expression_project(expression([literal(1)], prefix=0))
        at = raw.rfind(literal(1))
        bad = raw[:at+2] + struct.pack('<H', 7) + raw[at+4:]
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
    def test_original_independent_source_words_values_dynamic_refusal_and_reconstruction(self):
        from collections import Counter
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw); game = self.reader.read(raw)
        programs = []
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((p, blocks[p['block_id']].data) for p in f['programs'])
        programs.extend((p, game.segments[p['segment_id']].data) for p in d['global_events'])
        forms, roles, prefixes = Counter(), Counter(), Counter()
        for pr, block in programs:
            data = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), data)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] != 22:
                            self.assertNotIn('expression_getter_storage', q)
                            continue
                        at = q['offset']
                        self.assertEqual(struct.unpack_from('<H', data, at+2)[0], 22)
                        prefixes[struct.unpack_from('<H', data, at+4)[0]] += 1
                        roles[rec['role']] += 1
                        g = q['expression_getter_storage']; r = g['conditional_closed_integer_return']
                        eligible = data[at+6:at+10] == b'\xff\x00\x08\x00' and data[at+14:at+16] == bytes(2)
                        if eligible:
                            self.assertEqual(r, {'status': 'value', 'eax_raw_u32': int.from_bytes(data[at+10:at+14], 'little'),
                                                 'dx_raw_u16': 0, 'bx_raw_u16': 0, 'carry': False})
                        else:
                            self.assertEqual(r, {'status': 'unsupported_tokens'})
                        self.assertFalse(g['runtime_resolution']); forms[r['status']] += 1
        self.assertEqual(sum(forms.values()), 2461)
        self.assertEqual(dict(forms), ORIGINAL_FORMS)
        self.assertEqual(dict(roles), ORIGINAL_ROLES)
        self.assertEqual(dict(prefixes), ORIGINAL_PREFIXES)
