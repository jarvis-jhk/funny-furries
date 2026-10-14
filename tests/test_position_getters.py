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
from test_event_positions import position_program, position_project
from test_position_coordinates import coordinate_payload


def getter(x, y, ref=65535, flags=0):
    return events.decode_position_getter(coordinate_payload(16, x, y, ref, flags))


class PositionGetterTests(unittest.TestCase):
    def test_packed_axis_order_signed_boundaries_and_helper_failure_flag_discard(self):
        for x in (-32768, -32767, -7, -1, 0, 1, 32767):
            for y in (-32768, -1, 0, 13, 32767):
                out = getter(x, y)
                self.assertEqual(out['conditional_absolute_return'], {
                    'status': 'value', 'eax_raw_u32': ((x & 65535) << 16) | (y & 65535),
                    'dx_raw_u16': 0, 'bx_raw_u16': 0, 'carry': False})
                contract = out['conditional_normal_return']
                self.assertEqual(contract['eax_high_word'], 'helper_return_x_raw_u16')
                self.assertEqual(contract['eax_low_word'], 'helper_return_y_raw_u16')
                self.assertFalse(contract['helper_carry_preserved'])
                self.assertFalse(contract['carry'])
                self.assertEqual(contract['helper_failure_coordinate_values'], 'unknown')
                self.assertEqual(out['helper_input_bx_raw_u16'], 0)
                self.assertFalse(out['runtime_resolution'])
                self.assertEqual(out['caller_interpretation'], 'unknown')

    def test_every_reference_word_uses_sign_bit_without_live_state_or_sentinel_guess(self):
        for ref in range(65536):
            out = getter(-7, 13, ref)
            self.assertEqual(out['reference_raw_u16'], ref)
            probe = out['conditional_absolute_return']
            if ref & 0x8000:
                self.assertEqual((probe['status'], probe['eax_raw_u32']), ('value', 0xFFF9000D))
            else:
                self.assertEqual(probe, {'status': 'requires_live_object_state'})
            self.assertFalse(out['runtime_resolution'])

    def test_absolute_flags_opaque_tail_and_unknown_types_do_not_change_axis_transport(self):
        for flags in (0, 1, 2, 3, 4, 8, 0xFFFF):
            payload = coordinate_payload(16, -7, 13, 0x8001, flags) + b'opaque\xff'
            program = position_program([(16, payload), (999, payload)])
            rows = events.decode_rows(program)
            self.assertEqual(reconstruct_program({'rows': rows}), program)
            for rec in rows[0]['records']:
                q, unknown = rec['parameters']
                self.assertEqual(q['payload_hex'], payload.hex())
                self.assertEqual(q['position_getter_storage']['conditional_absolute_return']['eax_raw_u32'], 0xFFF9000D)
                self.assertEqual(q['position_coordinate_storage']['flags_raw_u16'], flags)
                self.assertNotIn('position_getter_storage', unknown)
                self.assertEqual(q['meaning'], 'unknown')

    def test_only_type16_both_roles_and_existing_position_views_strict_extent(self):
        parameters = [(k, coordinate_payload(k, -7, 13, 65535, 8)) for k in events.POSITION_PARAMETER_BYTES]
        program = position_program(parameters)
        rows = events.decode_rows(program)
        for rec in rows[0]['records']:
            for q in rec['parameters']:
                self.assertEqual('position_getter_storage' in q, q['type'] == 16)
                self.assertEqual(q['position_coordinate_storage']['x']['signed_i16'], -7)
                self.assertEqual(q['position_reference_storage']['references'][0]['status'], 'absolute_position_sentinel')
        for n in range(22):
            with self.assertRaises(project.InputError):
                events.decode_position_getter(bytes(n))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class PositionGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_scopes_roles_readable_reconstruction_and_false_general_coverage(self):
        raw, source = position_project([(16, coordinate_payload(16, -7, 13, 65535))])
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type16_position_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'position_resolution'):
            self.assertFalse(d['coverage'][key])
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), source)
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                self.assertEqual(q['position_getter_storage']['conditional_absolute_return']['eax_raw_u32'], 0xFFF9000D)
                self.assertFalse(q['position_getter_storage']['runtime_resolution'])
        self.assertEqual(events.readable(d).count('POSITION_GETTER '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw, _ = position_project([(16, coordinate_payload(16, -7, 13, 65535))])
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

    def test_late_short_position_refused_before_output_or_reporting(self):
        payload = coordinate_payload(16, -7, 13, 65535)
        raw, _ = position_project([(16, payload)])
        old = record('action', 2, 3, 0, [(16, payload)])
        new = record('action', 2, 3, 0, [(16, payload[:8]), (999, bytes(len(payload) - 12))])
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
    def test_original_source_spans_encoded_references_and_live_state_refusal(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw)
        programs = []
        game = self.reader.read(raw)
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for pr in f['programs']:
                programs.append((pr, blocks[pr['block_id']].data[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]))
        for pr in d['global_events']:
            data = game.segments[pr['segment_id']].data
            programs.append((pr, data[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]))
        observed = []
        for pr, original in programs:
            self.assertEqual(reconstruct_program(pr), original)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] != 16:
                            self.assertNotIn('position_getter_storage', q)
                            continue
                        at = q['offset'] + 4
                        data = original[at:at + q['bytes'] - 4]
                        ref, flags, x, y = struct.unpack_from('<HHhh', data)
                        self.assertEqual(bytes.fromhex(q['payload_hex']), data)
                        g = q['position_getter_storage']
                        self.assertEqual(g['reference_raw_u16'], ref)
                        self.assertEqual(g['conditional_absolute_return'], {'status': 'requires_live_object_state'})
                        self.assertFalse(g['runtime_resolution'])
                        self.assertEqual((flags, x, y, rec['role']), (8, 0, 0, 'action'))
                        observed.append((ref, int.from_bytes(data[18:20], 'little')))
        self.assertEqual(observed, [(0x4023, 0x17DA), (0x402B, 0x0866), (0x402A, 0x0810)])
