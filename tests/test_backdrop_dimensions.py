import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import backdrop_dump as backdrop, export_project as bundle, project_index as project
from test_backdrop_dump import header, project_bytes
from test_export_project import combined_project


def sized_header(kind=0, width=800, height=40, **kwargs):
    raw = bytearray(header(kind, **kwargs))
    struct.pack_into('<HH', raw, 34, width, height)
    return bytes(raw)


class DimensionTests(unittest.TestCase):
    def test_signed_asymmetric_boundaries_all_fills_and_opaque_neighbours(self):
        bounds = (0, 1, 32767, 32768, 32769, 65534, 65535)
        for fill in (0, 1, 2, 0x12):
            for width in bounds:
                for height in bounds:
                    raw = sized_header(width=width, height=height, fill=fill, image=5)
                    out = backdrop.decode_header(raw)
                    ann = out['quick_backdrop_dimension_inputs']
                    for axis, offset, target, word in (('width', 34, 26, width), ('height', 36, 28, height)):
                        with self.subTest(fill=fill, axis=axis, word=word):
                            self.assertEqual(ann[axis], {'header_offset': offset, 'placement_offset': target,
                                'raw_u16': word, 'signed_i16': word if word < 32768 else word - 65536})
                            self.assertEqual(struct.pack('<h', ann[axis]['signed_i16']), raw[offset:offset+2])
                    self.assertEqual(bytes.fromhex(out['header_hex']), raw)
                    self.assertEqual(out['header_sha256'], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(out['artwork']['fill_raw_u8'], fill)
                    self.assertEqual(out['artwork']['colors'][1]['raw_u32'], 0xFEDCBA98)
                    self.assertEqual(out['image_word_raw_u16'], 5)

    def test_ordinary_backdrop_header_words_stay_opaque(self):
        for width, height in ((0, 0), (800, 40), (65535, 32768)):
            out = backdrop.decode_header(sized_header(1, width, height, fill=255, image=5))
            self.assertIsNone(out['quick_backdrop_dimension_inputs'])
            self.assertEqual(out['artwork'], {'kind': 'image', 'image_id': 5})

    def test_zero_negative_and_sentinel_looking_values_have_no_geometry_claim(self):
        for word in (0, 32768, 65534, 65535):
            ann = backdrop.decode_header(sized_header(width=word, height=word))['quick_backdrop_dimension_inputs']
            self.assertEqual(set(ann), {'meaning', 'evidence', 'runtime_resolution', 'width', 'height'})
            self.assertEqual(ann['meaning'], 'quick_backdrop_dimension_inputs')
            self.assertEqual(ann['evidence'], 'original_runtime_header_refresh_and_rectangle_paths')
            self.assertFalse(ann['runtime_resolution'])
            self.assertEqual(ann['width']['raw_u16'], word)
            self.assertEqual(ann['height']['raw_u16'], word)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class DimensionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_local_global_headers_repeated_banks_and_no_resolution(self):
        local = sized_header(width=23, height=65529, fill=1, image=2)
        raw = project_bytes([local, sized_header(1, 32768, 65535, image=5), header(255)], repeated=True)
        doc = backdrop.backdrop_document(self.reader, raw)
        self.assertEqual((doc['schema_version'], doc['exporter']), (6, 'backdrop-dump/6'))
        self.assertTrue(doc['coverage']['quick_backdrop_dimension_inputs'])
        for key in ('runtime_rendering', 'global_reference_resolution', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][key])
        self.assertEqual(doc['frames'][0]['object_lists'], [])
        lists = doc['frames'][1]['object_lists']
        self.assertEqual(lists[0]['objects'], [])
        objects = lists[1]['objects']
        self.assertTrue(objects[0]['global'])
        ann = objects[0]['backdrop']['quick_backdrop_dimension_inputs']
        self.assertEqual((ann['width']['signed_i16'], ann['height']['signed_i16']), (23, -7))
        self.assertFalse(ann['runtime_resolution'])
        self.assertIsNone(objects[1]['backdrop']['quick_backdrop_dimension_inputs'])
        self.assertIsNone(objects[2]['backdrop'])
        global_quick = doc['global_object_lists'][0]['objects'][1]['backdrop']['quick_backdrop_dimension_inputs']
        self.assertEqual(global_quick['width']['raw_u16'], 0)
        self.assertEqual(backdrop.backdrop_document(self.reader, raw), doc)

    def test_standalone_bundle_repeats_and_immutable_annotation_difference(self):
        raw = combined_project()[0].replace(header(1, image=5), sized_header(width=65529, height=32768, fill=1, image=5))
        doc = backdrop.backdrop_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest['components']['backdrops.json'], {'exporter': 'backdrop-dump/6', 'schema_version': 6})
        self.assertEqual(json.loads(files['backdrops.json']), doc)
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch)), target)
            standalone = backdrop.save_backdrops(doc, Path(scratch))
            self.assertEqual(standalone.read_bytes(), files['backdrops.json'])
            self.assertEqual(backdrop.save_backdrops(doc, Path(scratch)).read_bytes(), files['backdrops.json'])
            changed = copy.deepcopy(doc)
            changed['frames'][1]['object_lists'][0]['objects'][1]['backdrop']['quick_backdrop_dimension_inputs']['width']['signed_i16'] += 1
            different_files = dict(files, **{'backdrops.json': bundle.json_bytes(changed)})
            different_manifest = copy.deepcopy(manifest)
            for entry in different_manifest['files']:
                if entry['file'] == 'backdrops.json':
                    entry['bytes'] = len(different_files[entry['file']])
                    entry['sha256'] = hashlib.sha256(different_files[entry['file']]).hexdigest()
            different_files['manifest.json'] = bundle.json_bytes(different_manifest)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(different_manifest, different_files, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_late_invalid_quick_fill_before_both_outputs_or_reporting(self):
        raw = combined_project()[0].replace(header(1, image=5), sized_header(fill=3, image=5))
        self.assert_refused(raw)

    def test_late_truncated_definition_before_both_outputs_or_reporting(self):
        raw = combined_project()[0]
        # Keep the late definition's segment size/next frame pointers intact,
        # while demanding one more header than is stored in that local list.
        game = self.reader.read(raw)
        level = game.levels()[1]
        block = next(b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2)
        at = level.offset + 6 + block.offset + 6
        malformed = bytearray(raw)
        struct.pack_into('<H', malformed, at, 5)
        self.assert_refused(bytes(malformed))

    def assert_refused(self, raw):
        for module, save in ((backdrop, 'save_backdrops'), (bundle, 'save_bundle')):
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=raw), \
                    patch.object(module, save) as write, patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_absolute_source_words_and_ordinary_opacity(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = backdrop.backdrop_document(self.reader, raw)
        game = self.reader.read(raw)
        lists = [(s.data, s.offset+6, out['objects'], True) for s, out in zip(
            [s for s in game.segments if s.ident == 6], doc['global_object_lists'])]
        for level, frame in zip(game.levels(), doc['frames']):
            lists += [(b.data, level.offset+6+b.offset+6, out['objects'], False) for b, out in zip(
                [b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2], frame['object_lists'])]
        counts = {0: 0, 1: 0}
        for data, at, outputs, global_list in lists:
            for obj, out in zip(self.reader.object_definitions(data, globals_have_blocks=global_list), outputs):
                if obj.object_type not in (0, 1):
                    self.assertIsNone(out['backdrop'])
                    continue
                counts[obj.object_type] += 1
                head = raw[at+obj.base:at+obj.base+68]
                self.assertEqual(head, data[obj.base:obj.base+68])
                self.assertEqual(bytes.fromhex(out['backdrop']['header_hex']), head)
                ann = out['backdrop']['quick_backdrop_dimension_inputs']
                if obj.object_type == 1:
                    self.assertIsNone(ann)
                    continue
                for axis, offset, target in (('width', 34, 26), ('height', 36, 28)):
                    bits = raw[at+obj.base+offset:at+obj.base+offset+2]
                    self.assertEqual(ann[axis]['header_offset'], offset)
                    self.assertEqual(ann[axis]['placement_offset'], target)
                    self.assertEqual(ann[axis]['raw_u16'], int.from_bytes(bits, 'little'))
                    self.assertEqual(ann[axis]['signed_i16'], int.from_bytes(bits, 'little', signed=True))
                self.assertFalse(ann['runtime_resolution'])
        self.assertEqual(counts, {0: 58, 1: 352})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(backdrop.backdrop_document(self.reader, raw), doc)


if __name__ == '__main__':
    unittest.main()
