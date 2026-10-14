import collections
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_positions import SIZES, position_payload, position_program, position_project
from test_event_dump import record, reconstruct_program


def coordinate_payload(kind, x, y, reference=0, flags=0):
    data = bytearray(position_payload(kind, reference, 0, b'own opaque tail'))
    struct.pack_into('<Hhh', data, 2, flags, x, y)
    return bytes(data)


class CoordinateTests(unittest.TestCase):
    def test_signed_boundaries_axes_and_raw_words_for_all_types(self):
        for kind in SIZES:
            for x, y in [(-32768, 32767), (-7, 13), (0, -1), (1, -32767)]:
                payload = coordinate_payload(kind, x, y, flags=0xFFFE)
                out = events.decode_position_coordinates(payload, kind)
                self.assertEqual(out['x'], {'payload_offset': 4, 'raw_u16': x & 65535, 'signed_i16': x})
                self.assertEqual(out['y'], {'payload_offset': 6, 'raw_u16': y & 65535, 'signed_i16': y})
                self.assertEqual(out['flags_payload_offset'], 2)
                self.assertEqual(out['flags_raw_u16'], 0xFFFE)
                self.assertFalse(out['runtime_resolution'])
                self.assertEqual(out['evidence'], 'cnc_position_helper_coordinate_inputs')

    def test_sentinels_and_flags_do_not_guess_encoded_or_dynamic_results(self):
        for ref in [0, 0x3FFF, 0x4000, 0x8000, 0xFFFD, 0xFFFE, 0xFFFF]:
            for flags in [0, 1, 2, 3, 6, 8, 10, 65535]:
                out = events.decode_position_coordinates(coordinate_payload(16, -7, 13, ref, flags), 16)
                self.assertEqual(out['word_usage'], 'absolute_xy' if ref in (65534, 65535) else 'context_dependent')
                self.assertFalse(out['runtime_resolution'])
                self.assertEqual(out['flags_raw_u16'], flags)
                self.assertNotIn('resolved_position', out)

    def test_both_roles_lossless_and_unknown_types_unannotated(self):
        parameters = [(kind, coordinate_payload(kind, -7, 13)) for kind in SIZES] + [(999, b'own bytes')]
        raw = position_program(parameters)
        rows = events.decode_rows(raw)
        for rec in rows[0]['records']:
            for param, (kind, payload) in zip(rec['parameters'], parameters):
                self.assertEqual(param['payload_hex'], payload.hex())
                self.assertEqual(param['meaning'], 'unknown')
                if kind == 999:
                    self.assertNotIn('position_coordinate_storage', param)
                else:
                    self.assertEqual(param['position_coordinate_storage']['x']['signed_i16'], -7)
                    self.assertEqual(param['position_coordinate_storage']['y']['signed_i16'], 13)

    def test_truncated_supported_layout_refuses_even_if_xy_words_fit(self):
        for kind, size in SIZES.items():
            for length in (0, 1, 2, 7, size - 5):
                with self.subTest(kind=kind, length=length), self.assertRaises(project.InputError):
                    events.decode_position_coordinates(bytes(length), kind)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class CoordinateContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_types_scopes_reference_annotations_and_readable_values(self):
        raw, source = position_project([(k, coordinate_payload(k, -7, 13, 65535, 10)) for k in SIZES])
        doc = events.event_document(self.reader, raw)
        self.assertEqual((doc['schema_version'], doc['exporter']), (37, 'event-dump/37'))
        self.assertTrue(doc['coverage']['position_coordinate_storage'])
        self.assertFalse(doc['coverage']['position_resolution'])
        programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
        for program in programs:
            self.assertEqual(reconstruct_program(program), source)
            for rec in program['rows'][0]['records']:
                for param in rec['parameters']:
                    self.assertEqual(param['position_coordinate_storage'], events.decode_position_coordinates(
                        bytes.fromhex(param['payload_hex']), param['type']))
                    self.assertEqual(param['position_reference_storage']['references'][0]['status'], 'absolute_position_sentinel')
        text = events.readable(doc)
        self.assertEqual(text.count('POSITION_COORDINATES '), 40)
        self.assertIn('"signed_i16": -7', text)
        self.assertIn('"signed_i16": 13', text)
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_bundle_bytes_repeat_and_pinned_converter_preserves_coordinate_words(self):
        from klikback.core.common import reconstruct_event_test as independent
        raw, _ = position_project([(k, coordinate_payload(k, -32768, 32767, 7, 65535)) for k in SIZES])
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest['components']['events.json'], {'exporter': 'event-dump/37', 'schema_version': 37})
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch)), target)
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, files)
        for kind in SIZES:
            data = coordinate_payload(kind, -32768, 32767, 7, 65535)
            param = struct.pack('<HH', len(data) + 4, kind) + data
            mapped = bytearray(param)
            independent.remap_object_position_parameter(mapped, 0, len(mapped), kind, {7: 123})
            self.assertEqual(mapped[6:12], param[6:12])
            self.assertEqual(int.from_bytes(mapped[4:6], 'little'), 123)

    def test_late_malformed_coordinate_parameter_precedes_every_output_and_report(self):
        raw, _ = position_project([(18, coordinate_payload(18, -7, 13))])
        old = record('action', 2, 3, 0, [(18, coordinate_payload(18, -7, 13))])
        # Keep the container/row extent identical; the final type18 parameter
        # declares eight complete XY input bytes but lacks its supported tail.
        payload = coordinate_payload(18, -7, 13)
        new = record('action', 2, 3, 0, [(18, payload[:8]), (999, bytes(len(payload) - 12))])
        self.assertEqual(len(old), len(new))
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        bad = raw[:at] + new + raw[at + len(old):]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                 patch.object(project, 'load_reader', return_value=self.reader), \
                 patch.object(Path, 'read_bytes', return_value=bad), \
                 patch.object(project, 'save_export') as write, patch.object(bundle, 'save_bundle') as save, \
                 patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called()
                save.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_source_spans_independent_words_and_converter_agreement(self):
        from klikback.core.common import reconstruct_event_test as independent
        source = Path(os.environ['FF_TEST_PROJECT'])
        raw = source.read_bytes()
        doc = events.event_document(self.reader, raw)
        programs = []
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            _, blocks = self.reader.level_blocks(level.data)
            for p in frame['programs']:
                programs.append((p, blocks[p['block_id']].data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        game = self.reader.read(raw)
        for p in doc['global_events']:
            data = game.segments[p['segment_id']].data
            programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        counts, flags = collections.Counter(), collections.Counter()
        for program, original in programs:
            self.assertEqual(reconstruct_program(program), original)
            for row in program['rows']:
                for rec in row['records']:
                    for param in rec['parameters']:
                        if param['type'] not in SIZES:
                            self.assertNotIn('position_coordinate_storage', param)
                            continue
                        at = param['offset'] + 4
                        data = original[at:at + param['bytes'] - 4]
                        out = param['position_coordinate_storage']
                        expected_x = int.from_bytes(data[4:6], 'little', signed=True)
                        expected_y = int.from_bytes(data[6:8], 'little', signed=True)
                        self.assertEqual(out['x']['signed_i16'], expected_x)
                        self.assertEqual(out['y']['signed_i16'], expected_y)
                        self.assertEqual(out['x']['raw_u16'], int.from_bytes(data[4:6], 'little'))
                        self.assertEqual(out['y']['raw_u16'], int.from_bytes(data[6:8], 'little'))
                        self.assertEqual(out['flags_raw_u16'], int.from_bytes(data[2:4], 'little'))
                        self.assertEqual(out['word_usage'], 'context_dependent')
                        self.assertFalse(out['runtime_resolution'])
                        parameter = bytearray(original[at - 4:at + len(data)])
                        independent.remap_object_position_parameter(parameter, 0, len(parameter), param['type'], None)
                        self.assertEqual(parameter[6:12], data[2:8])
                        counts[param['type']] += 1
                        flags[out['flags_raw_u16']] += 1
        self.assertEqual(counts, {9: 1150, 18: 110, 16: 3})
        self.assertEqual(flags, {10: 570, 2: 30, 6: 80, 8: 583})
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), hashlib.sha256(raw).digest())
        self.assertEqual(events.event_document(self.reader, raw), doc)


if __name__ == '__main__':
    unittest.main()
