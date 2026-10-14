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
from test_event_dump import record, reconstruct_program
from test_event_object_parameters import program
from test_event_positions import position_project


def payload(value=0xA1B2C3D4, control=0x8000, middle=b'\xff\x7f\xaa\x55', tail=b''):
    return struct.pack('<I', value) + middle + struct.pack('<H', control) + tail


class FixedValueGetterTests(unittest.TestCase):
    def test_every_control_word_wraps_without_masking_or_comparison_inference(self):
        for control in range(65536):
            out = events.decode_fixed_value_getter(payload(control=control))
            self.assertEqual((out['control_payload_offset'], out['control_raw_u16']), (8, control))
            self.assertEqual(out['conditional_getter_return']['bx_raw_u16'], (control + 1) & 65535)
            self.assertFalse(out['conditional_getter_return']['carry'])
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(out['caller_interpretation'], 'unknown')
            self.assertNotIn('operation', out)
            self.assertNotIn('condition_result', out)

    def test_dword_transport_middle_and_suffix_preserved_no_units_or_signedness(self):
        for value in (0, 1, 65535, 65536, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            for middle in (bytes(4), b'\xff' * 4, bytes.fromhex('deadbeef')):
                out = events.decode_fixed_value_getter(payload(value, 65535, middle, b'\xffopaque\0tail'))
                self.assertEqual((out['value_payload_offset'], out['value_raw_u32']), (0, value))
                self.assertEqual(out['opaque_middle_hex'], middle.hex())
                self.assertEqual(out['opaque_suffix_hex'], b'\xffopaque\0tail'.hex())
                ret = out['conditional_getter_return']
                self.assertEqual((ret['eax_raw_u32'], ret['bx_raw_u16'], ret['carry']), (value, 0, False))
                self.assertEqual(ret['dx'], 'preserved_incoming_word_not_a_new_value_tag')
                self.assertNotIn('signed_value', out)
                self.assertNotIn('units', out)

    def test_exact_type_both_roles_and_lossless_reconstruction(self):
        data = payload(tail=b'\xffown\0tail')
        source = program([(41, data), (42, data), (43, data), (999, data)])
        rows = events.decode_rows(source)
        self.assertEqual(reconstruct_program({'rows': rows}), source)
        for rec in rows[0]['records']:
            for q in rec['parameters']:
                self.assertEqual('fixed_value_getter_storage' in q, q['type'] == 42)
                self.assertEqual(q['payload_hex'], data.hex())
                self.assertEqual(q['meaning'], 'unknown')
                self.assertNotIn('scalar_getter_storage', q)
                self.assertNotIn('comparison_prefix_storage', q)

    def test_short_extents_refused_even_when_dword_already_complete(self):
        for length in range(10):
            with self.assertRaises(project.InputError):
                events.decode_fixed_value_getter(bytes(length))
            with self.assertRaises(project.InputError):
                events.decode_rows(program([(42, bytes(length))]))
        self.assertEqual(events.decode_fixed_value_getter(bytes(10))['control_raw_u16'], 0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class FixedValueGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_scopes_roles_text_and_false_semantic_coverage(self):
        raw, source = position_project([(42, payload())])
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type42_fixed_value_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'global_reference_resolution'):
            self.assertFalse(d['coverage'][key])
        count = 0
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), source)
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                self.assertEqual(q['fixed_value_getter_storage']['conditional_getter_return']['bx_raw_u16'], 32769)
                self.assertFalse(q['fixed_value_getter_storage']['runtime_resolution'])
                count += 1
        self.assertEqual(count, 10)
        self.assertEqual(events.readable(d).count('FIXED_VALUE_GETTER '), count)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw, _ = position_project([(42, payload())])
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
            updated = json.loads(changed['manifest.json'])
            for component in updated['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(updated)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(updated, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_short_type42_refused_before_writes_or_fault_reporting(self):
        raw, _ = position_project([(42, payload(tail=bytes(2)))])
        old = record('action', 2, 3, 0, [(42, payload(tail=bytes(2)))])
        new = record('action', 2, 3, 0, [(42, payload()[:8]), (999, b'')])
        self.assertEqual(len(old), len(new))
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        bad = raw[:at] + new + raw[at + len(old):]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as write, \
                    patch.object(bundle, 'save_bundle') as save, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called(); save.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_has_no_type42_and_all_program_bytes_stay_lossless(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes(); d = events.event_document(self.reader, raw)
        game = self.reader.read(raw); count = 0
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for pr in f['programs']:
                source = blocks[pr['block_id']].data[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
                self.assertEqual(reconstruct_program(pr), source)
        for pr in d['global_events']:
            source = game.segments[pr['segment_id']].data
            self.assertEqual(reconstruct_program(pr), source[pr['program_offset']:pr['program_offset'] + pr['program_bytes']])
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        self.assertNotEqual(q['type'], 42)
                        self.assertNotIn('fixed_value_getter_storage', q)
                        count += 1
        self.assertEqual(count, 8160)
        self.assertEqual(path.read_bytes(), raw)
