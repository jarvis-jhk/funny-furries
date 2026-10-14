import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import export_project as bundle, frame_layout as layout, project_index as project
from test_frame_layout import reconstruct, synthetic_layout


class DimensionTests(unittest.TestCase):
    def test_signed_boundaries_asymmetric_axes_opaque_header_and_both_extents(self):
        bounds = (0, 1, 32767, 32768, 32769, 65534, 65535)
        for extent in (0x78, 0xb8):
            for width in bounds:
                for height in bounds:
                    header = bytearray((i * 37 + 11) % 256 for i in range(extent))
                    struct.pack_into('<HH', header, 4, width, height)
                    raw = bytes(header)
                    out = layout.decode_dimension_inputs(raw)
                    for axis, offset, word in (('width', 4, width), ('height', 6, height)):
                        with self.subTest(extent=extent, axis=axis, word=word):
                            self.assertEqual(out[axis], {'header_offset': offset, 'raw_u16': word,
                                             'signed_i16': word if word < 32768 else word - 65536})
                            self.assertEqual(struct.pack('<h', out[axis]['signed_i16']), raw[offset:offset+2])
                    self.assertEqual(bytes(header), raw)

    def test_zero_negative_and_sentinel_bits_are_preserved_without_geometry_claim(self):
        for word in (0, 32768, 65534, 65535):
            header = bytearray(0x78)
            struct.pack_into('<HH', header, 4, word, word)
            out = layout.decode_dimension_inputs(bytes(header))
            self.assertEqual(out['meaning'], 'frame_dimension_inputs')
            self.assertEqual(out['evidence'], 'original_runtime_frame_size_and_clipping_paths')
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(set(out), {'meaning', 'evidence', 'runtime_resolution', 'width', 'height'})
            self.assertEqual(out['width']['raw_u16'], word)
            self.assertEqual(out['height']['raw_u16'], word)

    def test_unsupported_header_shapes_refused(self):
        for length in (0, 1, 7, 8, 0x77, 0x79, 0xb7, 0xb9, 0x100):
            with self.subTest(length=length), self.assertRaises(project.InputError):
                layout.decode_dimension_inputs(bytes(length))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class DimensionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_headers_empty_frames_repeated_blocks_and_prior_fields(self):
        raw = synthetic_layout()
        doc = layout.layout_document(self.reader, raw)
        self.assertEqual((doc['schema_version'], doc['exporter']), (5, 'frame-layout/5'))
        self.assertTrue(doc['coverage']['frame_dimension_inputs'])
        for key in ('placement_semantics', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][key])
        levels = self.reader.read(raw).levels()
        for frame, level in zip(doc['frames'], levels):
            header = bytes.fromhex(frame['header_hex'])
            self.assertEqual(header, level.data[:frame['header_bytes']])
            for axis, offset in (('width', 4), ('height', 6)):
                self.assertEqual(frame['dimension_inputs'][axis]['raw_u16'], int.from_bytes(header[offset:offset+2], 'little'))
            self.assertEqual(frame['header_meaning'], 'unknown')
            _, blocks = self.reader.level_blocks(level.data)
            for placement in frame['placements']:
                self.assertEqual(reconstruct(placement), blocks[placement['block_id']].data)
                for rec in placement['records']:
                    self.assertIn('object_slot_probe', rec)
                    self.assertIn('coordinate_inputs', rec)
                    self.assertIn('creation_type_input', rec)
        self.assertEqual([f['header_bytes'] for f in doc['frames']], [0xb8, 0x78])
        self.assertEqual(doc['frames'][0]['placements'], [])
        self.assertEqual(doc['frames'][1]['placements'][1]['records'], [])
        self.assertEqual(layout.layout_document(self.reader, raw), doc)

    def test_bundle_and_standalone_json_repeats_and_immutable_difference(self):
        raw = synthetic_layout()
        doc = layout.layout_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest['components']['frame-layout.json'], {'exporter': 'frame-layout/5', 'schema_version': 5})
        self.assertEqual(json.loads(files['frame-layout.json']), doc)
        self.assertFalse(manifest['coverage']['arena_geometry'])
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch)), target)
            single = layout.save_layout(doc, Path(scratch))
            self.assertEqual(single.read_bytes(), files['frame-layout.json'])
            self.assertEqual(layout.save_layout(doc, Path(scratch)).read_bytes(), single.read_bytes())
            changed = copy.deepcopy(doc)
            changed['frames'][0]['dimension_inputs']['width']['signed_i16'] += 1
            different_files = dict(files, **{'frame-layout.json': bundle.json_bytes(changed)})
            different_manifest = copy.deepcopy(manifest)
            for entry in different_manifest['files']:
                if entry['file'] == 'frame-layout.json':
                    entry['bytes'] = len(different_files[entry['file']])
                    entry['sha256'] = hashlib.sha256(different_files[entry['file']]).hexdigest()
            different_files['manifest.json'] = bundle.json_bytes(different_manifest)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(different_manifest, different_files, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_late_malformed_placement_precedes_output_and_reporting(self):
        raw = synthetic_layout()[:-2] + struct.pack('<H', 1)
        for module, save in ((layout, 'save_layout'), (bundle, 'save_bundle')):
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(module, save) as write, patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called()
                report.assert_not_called()

    def test_late_header_extent_guard_precedes_writes_and_reporting(self):
        raw = synthetic_layout()
        actual = layout.decode_dimension_inputs
        calls = 0
        def invalid_extent(header):
            nonlocal calls
            calls += 1
            # Inject a bad late extent at the decoder boundary, then execute
            # its real guard; both CLI transactions must remain unwritten.
            return actual(header[:-1] if calls == 2 else header)
        for module, save in ((layout, 'save_layout'), (bundle, 'save_bundle')):
            calls = 0
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(layout, 'decode_dimension_inputs', side_effect=invalid_extent), \
                    patch.object(module, save) as write, patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                self.assertEqual(calls, 2)
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_header_word_reads_and_unchanged_input(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = layout.layout_document(self.reader, raw)
        dimensions = []
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            # Independent absolute spans in the source, without decoder helpers.
            header_at = level.offset + 6
            for axis, offset in (('width', 4), ('height', 6)):
                bits = raw[header_at+offset:header_at+offset+2]
                self.assertEqual(bits, level.data[offset:offset+2])
                ann = frame['dimension_inputs'][axis]
                self.assertEqual(ann['header_offset'], offset)
                self.assertEqual(ann['raw_u16'], int.from_bytes(bits, 'little'))
                self.assertEqual(ann['signed_i16'], int.from_bytes(bits, 'little', signed=True))
            dimensions.append(tuple(frame['dimension_inputs'][axis]['signed_i16'] for axis in ('width', 'height')))
            self.assertFalse(frame['dimension_inputs']['runtime_resolution'])
            self.assertEqual(bytes.fromhex(frame['header_hex']), raw[header_at:header_at+frame['header_bytes']])
        self.assertEqual(dimensions, [(350, 150)] + [(800, 600)] * 12)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(doc, layout.layout_document(self.reader, raw))


if __name__ == '__main__':
    unittest.main()
