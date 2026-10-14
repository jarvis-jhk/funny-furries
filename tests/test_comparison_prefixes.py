import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import expression, token, expression_program, expression_project


def literal(value):
    return token(255, struct.pack('<i', value))


class ComparisonPrefixTests(unittest.TestCase):
    def test_all_prefix_words_getter_wrap_mask_signed_operation_and_unknown_indices(self):
        names = ['equal', 'not_equal', 'less_or_equal', 'less', 'greater_or_equal', 'greater']
        for raw in range(65536):
            out = events.decode_comparison_prefix(struct.pack('<H', raw) + b'opaque')
            self.assertEqual(out['raw_u16'], raw)
            self.assertEqual(out['getter_bx_on_normal_expression_return_raw_u16'], (raw + 1) % 65536)
            self.assertFalse(out['getter_carry_on_normal_expression_return'])
            c = out['conditional_integer_consumer']
            index = raw % 32768
            self.assertEqual(c['index_raw_u16'], index)
            self.assertEqual(c['opaque_high_bit_raw_u16'], raw - index)
            self.assertEqual(c['operation'], names[index] if index < 6 else None)
            self.assertEqual(c['status'], 'table_entry' if index < 6 else 'outside_proven_table')
            self.assertEqual((c['operand_bits'], c['signed']), (32, True))
            self.assertIsNone(c['left_value'])
            self.assertIsNone(c['condition_result'])
            self.assertFalse(out['runtime_resolution'])

    def test_type23_only_both_roles_raw_program_and_text_preserved(self):
        payload = expression([literal(-2147483648)], prefix=0x8003, suffix=b'own\xfftail')
        for kind in [*sorted(events.EXPRESSION_TYPES), 999]:
            raw = expression_program(payload, kind)
            out = events.decode_rows(raw)
            self.assertEqual(reconstruct_program({'rows': out}), raw)
            for rec in out[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('comparison_prefix_storage' in q, kind == 23)
                if kind == 23:
                    self.assertEqual(q['comparison_prefix_storage']['conditional_integer_consumer']['operation'], 'less')
                    self.assertEqual(q['expression_storage']['suffix_hex'], b'own\xfftail'.hex())
                    self.assertEqual(q['meaning'], 'unknown')

    def test_dynamic_fault_empty_and_unknown_prefix_never_become_condition_results(self):
        forms = [[], [token(0x1FF)], [literal(-2147483648), token(0x800), literal(-1)],
                 [token(0xFFFF), literal(7), token(0xFEFF)]]
        for items in forms:
            raw = expression_program(expression(items, prefix=0xFFFF), 23)
            q = events.decode_rows(raw)[0]['records'][0]['parameters'][0]
            out = q['comparison_prefix_storage']
            self.assertEqual(out['getter_bx_on_normal_expression_return_raw_u16'], 0)
            self.assertIsNone(out['conditional_integer_consumer']['operation'])
            self.assertIsNone(out['conditional_integer_consumer']['condition_result'])
            self.assertFalse(out['runtime_resolution'])

    def test_truncated_prefix_and_supported_expression_validation(self):
        for payload in (b'', b'\xff'):
            with self.assertRaises(project.InputError):
                events.decode_comparison_prefix(payload)
        for payload in (b'', b'\xff', bytes(2), bytes(2) + token(255, bytes(3)) + bytes(2)):
            with self.assertRaises(project.InputError):
                events.decode_rows(expression_program(payload, 23))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ComparisonPrefixContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def make_project(self, payload):
        raw, _ = expression_project(payload)
        size = 4 + len(payload)
        return raw.replace(struct.pack('<HH', size, 22), struct.pack('<HH', size, 23))

    def test_frame_global_both_roles_readable_and_raw_reconstruction(self):
        payload = expression([literal(-7)], prefix=5)
        raw = self.make_project(payload)
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['comparison_prefix_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation'):
            self.assertFalse(d['coverage'][key])
        programs = [p for f in d['frames'] for p in f['programs']] + d['global_events']
        for p in programs:
            self.assertEqual(reconstruct_program(p), expression_program(payload, 23))
            for rec in p['rows'][0]['records']:
                self.assertEqual(rec['parameters'][0]['comparison_prefix_storage']['conditional_integer_consumer']['operation'], 'greater')
        text = events.readable(d)
        self.assertEqual(text.count('COMPARISON_PREFIX '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_repeat_immutable_and_previous_fields(self):
        raw = self.make_project(expression([literal(-17)], prefix=0x8004))
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
            # Component hashes must agree so refusal exercises immutability.
            import hashlib, json
            newmanifest = json.loads(changed['manifest.json'])
            for component in newmanifest['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(newmanifest)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(newmanifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_malformed_before_any_output_or_fault_report(self):
        raw = self.make_project(expression([literal(1)], prefix=0))
        at = raw.rfind(token(255, struct.pack('<i', 1)))
        bad = raw[:at + 2] + struct.pack('<H', 7) + raw[at + 4:]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as savebundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called()
                savebundle.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_absolute_source_prefixes_and_independent_token_walk(self):
        from collections import Counter
        from klikback.core.common.event_object_registry import expression_object_slots
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        programs = []
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((p, blocks[p['block_id']].data) for p in f['programs'])
        programs.extend((p, game.segments[p['segment_id']].data) for p in d['global_events'])
        counts, forms = Counter(), Counter()
        names = {0: 'equal', 1: 'not_equal', 2: 'less_or_equal', 3: 'less', 4: 'greater_or_equal', 5: 'greater'}
        for p, data in programs:
            data = data[p['program_offset']:p['program_offset'] + p['program_bytes']]
            self.assertEqual(reconstruct_program(p), data)
            for row in p['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] != 23:
                            self.assertNotIn('comparison_prefix_storage', q)
                            continue
                        at = q['offset']
                        self.assertEqual(int.from_bytes(data[at + 2:at + 4], 'little'), 23)
                        list(expression_object_slots(data, at, at + q['bytes']))
                        prefix = int.from_bytes(data[at + 4:at + 6], 'little')
                        c = q['comparison_prefix_storage']
                        self.assertEqual(c['raw_u16'], prefix)
                        self.assertEqual(c['conditional_integer_consumer']['operation'], names[prefix])
                        self.assertIsNone(c['conditional_integer_consumer']['condition_result'])
                        counts[(rec['role'], prefix)] += 1
                        forms[q['expression_storage']['constant_integer_evaluation']['status']] += 1
        self.assertEqual(counts, {('condition', 0): 578, ('condition', 1): 60,
                                 ('condition', 2): 92, ('condition', 3): 461, ('condition', 5): 209})
        self.assertEqual(forms, {'value': 1378, 'unsupported_tokens': 22})
