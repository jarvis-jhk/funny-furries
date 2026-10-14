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
from test_event_expressions import expression, expression_program, expression_project, token

WORD_TYPES = {3, 4, 5, 10, 12, 14, 15, 17, 26, 32, 34}
DWORD_TYPES = {2, 24, 29}


class ScalarGetterTests(unittest.TestCase):
    def test_every_word_zero_extended_all_exact_types_opaque_suffix_and_limits(self):
        self.assertEqual(events.SCALAR_WORD_TYPES, WORD_TYPES)
        for kind in WORD_TYPES:
            for value in range(65536):
                out = events.decode_scalar_getter(struct.pack('<H', value) + b'\xffopaque', kind)
                self.assertEqual((out['payload_offset'], out['stored_bits'], out['stored_raw_unsigned']), (0, 16, value))
                self.assertEqual(out['opaque_suffix_hex'], b'\xffopaque'.hex())
                ret = out['conditional_getter_return']
                self.assertEqual((ret['eax_raw_u32'], ret['extension'], ret['bx_raw_u16'], ret['carry']), (value, 'zero_extend', 0, False))
                self.assertEqual(ret['dx'], 'preserved_incoming_word_not_a_new_value_tag')
                self.assertEqual(out['caller_interpretation'], 'unknown')
                self.assertFalse(out['runtime_resolution'])

    def test_dword_bits_preserved_no_sign_or_unit_inference(self):
        self.assertEqual(events.SCALAR_DWORD_TYPES, DWORD_TYPES)
        for kind in DWORD_TYPES:
            for value in (0, 1, 0xFFFF, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xA1B2C3D4):
                out = events.decode_scalar_getter(struct.pack('<I', value) + b'\x99\x88', kind)
                self.assertEqual((out['stored_bits'], out['stored_raw_unsigned']), (32, value))
                self.assertEqual(out['conditional_getter_return']['eax_raw_u32'], value)
                self.assertEqual(out['conditional_getter_return']['extension'], 'none')
                self.assertEqual(out['opaque_suffix_hex'], '9988')
                self.assertNotIn('signed_value', out)
                self.assertFalse(out['runtime_resolution'])

    def test_only_supported_types_both_roles_reconstruct_raw_and_type15_dual_view(self):
        payload = expression([token(255, struct.pack('<i', -7))], prefix=0xFEDC, suffix=b'\xfftail')
        for kind in range(56):
            # Other supported layouts have their own minimum extents.
            if kind in (1, 9, 16, 18, 21, 38):
                continue
            program = expression_program(payload, kind)
            rows = events.decode_rows(program)
            self.assertEqual(reconstruct_program({'rows': rows}), program)
            for rec in rows[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('scalar_getter_storage' in q, kind in WORD_TYPES | DWORD_TYPES)
                if kind == 15:
                    self.assertEqual(q['scalar_getter_storage']['conditional_getter_return']['eax_raw_u32'], 0xFEDC)
                    self.assertEqual(q['expression_storage']['constant_integer_evaluation']['value_signed_i32'], -7)
                    self.assertEqual(q['meaning'], 'unknown')
                if kind == 26 and rec['role'] == 'action':
                    self.assertEqual(q['frame_target_storage']['target_raw_u16'], 0xFEDC)

    def test_truncated_supported_scalar_and_unknown_type_refused(self):
        for kind in WORD_TYPES | DWORD_TYPES:
            extent = 2 if kind in WORD_TYPES else 4
            for length in range(extent):
                with self.subTest(kind=kind, length=length), self.assertRaises(project.InputError):
                    events.decode_rows(expression_program(bytes(length), kind))
        with self.assertRaises(project.InputError):
            events.decode_scalar_getter(bytes(10), 22)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ScalarGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def make_project(self, kind=29, payload=bytes.fromhex('d4c3b2a1')):
        raw, _ = expression_project(payload)
        return raw.replace(struct.pack('<HH', 4 + len(payload), 22), struct.pack('<HH', 4 + len(payload), kind))

    def test_frame_global_both_roles_text_and_unresolved_semantics(self):
        raw = self.make_project()
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['immediate_scalar_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation'):
            self.assertFalse(d['coverage'][key])
        for pr in [pr for f in d['frames'] for pr in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), expression_program(bytes.fromhex('d4c3b2a1'), 29))
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                self.assertEqual(q['scalar_getter_storage']['conditional_getter_return']['eax_raw_u32'], 0xA1B2C3D4)
                self.assertFalse(q['scalar_getter_storage']['runtime_resolution'])
        self.assertEqual(events.readable(d).count('SCALAR_GETTER '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw = self.make_project(10, b'\xff\xffopaque')
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

    def test_late_truncated_scalar_refused_before_output_or_reporting(self):
        raw = self.make_project(14, b'\xfe\xff')
        at = raw.rfind(struct.pack('<HH', 6, 14))
        # DWORD type requires four bytes; WORD fixture retains only two.
        bad = raw[:at + 2] + struct.pack('<H', 29) + raw[at + 4:]
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
    def test_original_independent_source_scalar_words_counts_and_reconstruction(self):
        from collections import Counter
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        programs = []
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((p, blocks[p['block_id']].data) for p in f['programs'])
        programs.extend((p, game.segments[p['segment_id']].data) for p in d['global_events'])
        counts = Counter()
        for pr, block in programs:
            data = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), data)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        at = q['offset']
                        kind = int.from_bytes(data[at + 2:at + 4], 'little')
                        self.assertEqual(kind, q['type'])
                        if kind not in WORD_TYPES | DWORD_TYPES:
                            self.assertNotIn('scalar_getter_storage', q)
                            continue
                        size = 2 if kind in WORD_TYPES else 4
                        value = int.from_bytes(data[at + 4:at + 4 + size], 'little')
                        s = q['scalar_getter_storage']
                        self.assertEqual(s['stored_raw_unsigned'], value)
                        self.assertEqual(s['conditional_getter_return']['eax_raw_u32'], value)
                        self.assertEqual(s['opaque_suffix_hex'], data[at + 4 + size:at + q['bytes']].hex())
                        self.assertFalse(s['runtime_resolution'])
                        counts[kind] += 1
        self.assertEqual(counts, {2: 7, 10: 197, 14: 16, 17: 246, 26: 2, 29: 307, 32: 18})
        self.assertEqual(sum(counts.values()), 793)
