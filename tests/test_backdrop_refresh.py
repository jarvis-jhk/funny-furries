import copy
from contextlib import redirect_stderr
import hashlib
import io
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


def refresh_header(kind=0, high=0, fill=0, image=5):
    raw = bytearray(header(kind, fill, image))
    raw[33], raw[43] = 0xA7, high
    struct.pack_into('<HHI', raw, 34, 65529, 23, 0x96870080)
    # Word50 and neighbours deliberately conflict with image/type words.
    struct.pack_into('<I', raw, 50, 0xFEDCBA98)
    return bytes(raw)


def expected_writes(raw):
    # Independent fixed source/destination spans, also compared with original
    # machine execution in local evidence. Neighbours must never enter a word.
    fields = [(50, 12, 4), (42, 6, 2)]
    if raw[42] == 0:
        fields += [(24, 16, 4), (28, 20, 4), (32, 24, 2), (34, 26, 2), (36, 28, 2)]
    fields += [(54, 8, 2)]
    return [{'header_offset': at, 'placement_offset': target, 'bytes': count,
             'raw_unsigned': int.from_bytes(raw[at:at+count], 'little'),
             'and_mask': 4095 if at == 42 else None,
             'written_unsigned': int.from_bytes(raw[at:at+count], 'little') & (4095 if at == 42 else (1 << (8*count))-1)}
            for at, target, count in fields]


class RefreshTests(unittest.TestCase):
    def test_all_type_high_bytes_mask_and_order_with_opaque_neighbours(self):
        for kind in (0, 1):
            for high in range(256):
                with self.subTest(kind=kind, high=high):
                    raw = refresh_header(kind, high)
                    out = backdrop.decode_header(raw)
                    ann = out['placement_refresh_inputs']
                    self.assertEqual(ann['writes'], expected_writes(raw))
                    self.assertEqual(ann['dispatch_low_byte'], kind)
                    self.assertEqual(ann['writes'][1]['written_unsigned'], kind + ((high & 15) << 8))
                    self.assertEqual(bytes.fromhex(out['header_hex']), raw)
                    self.assertEqual(out['header_sha256'], hashlib.sha256(raw).hexdigest())

    def test_quick_full_fill_word_colors_sizes_and_unused_image_still_copied(self):
        for fill in (0, 1, 2, 16, 17, 18):
            raw = refresh_header(fill=fill, image=65535)
            out = backdrop.decode_header(raw)
            writes = {w['placement_offset']: w for w in out['placement_refresh_inputs']['writes']}
            self.assertEqual(writes[24]['written_unsigned'], 0xA700 | fill)
            self.assertEqual(writes[8]['written_unsigned'], 65535)
            self.assertEqual(writes[16]['written_unsigned'], 0x7F563412)
            self.assertEqual(writes[20]['written_unsigned'], 0xFEDCBA98)
            self.assertEqual((writes[26]['written_unsigned'], writes[28]['written_unsigned']), (65529, 23))
            self.assertEqual(out['artwork']['image_id'], 65535 if fill & 15 == 1 else None)
            self.assertEqual(out['quick_backdrop_dimension_inputs']['width']['signed_i16'], -7)

    def test_ordinary_quick_words_not_written_no_semantics_claim(self):
        raw = refresh_header(1, high=0xFF, fill=255)
        ann = backdrop.decode_header(raw)['placement_refresh_inputs']
        self.assertEqual([w['placement_offset'] for w in ann['writes']], [12, 6, 8])
        self.assertEqual(ann['writes'][0]['written_unsigned'], 0xFEDCBA98)
        self.assertEqual(set(ann), {'meaning', 'evidence', 'runtime_resolution', 'dispatch_low_byte', 'writes'})
        self.assertEqual(ann['meaning'], 'backdrop_placement_refresh_inputs')
        self.assertEqual(ann['evidence'], 'original_runtime_complete_header_refresh_helper')
        self.assertFalse(ann['runtime_resolution'])

    def test_unsupported_shapes_and_types_not_refreshable(self):
        for raw in (b'', refresh_header()[:-1], refresh_header()+b'x', header(2), header(255), header(fill=3)):
            with self.subTest(raw=raw), self.assertRaises(project.InputError):
                backdrop.decode_header(raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class RefreshContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_local_global_differences_empty_lists_repeated_banks_remain_unresolved(self):
        doc = backdrop.backdrop_document(self.reader, project_bytes([refresh_header(1, 255), refresh_header(), header(255)], repeated=True))
        self.assertEqual((doc['schema_version'], doc['exporter']), (6, 'backdrop-dump/6'))
        self.assertTrue(doc['coverage']['backdrop_placement_refresh_inputs'])
        for field in ('runtime_rendering', 'global_reference_resolution', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][field])
        self.assertEqual(doc['frames'][0]['object_lists'], [])
        self.assertEqual(doc['frames'][1]['object_lists'][0]['objects'], [])
        objs = doc['frames'][1]['object_lists'][1]['objects']
        local = objs[0]['backdrop']['placement_refresh_inputs']
        global_ = doc['global_object_lists'][0]['objects'][0]['backdrop']['placement_refresh_inputs']
        self.assertTrue(objs[0]['global'])
        self.assertNotEqual(local['writes'], global_['writes'])
        self.assertFalse(local['runtime_resolution'])
        self.assertIsNone(objs[2]['backdrop'])
        self.assertEqual(len(objs[0]['backdrop']['ordinary_backdrop_image_candidates']['candidates']), 2)

    def test_bundle_standalone_immutable_repeats_and_version(self):
        raw = combined_project()[0].replace(header(1, image=5), refresh_header(1, high=255))
        doc = backdrop.backdrop_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest['components']['backdrops.json'], {'exporter': 'backdrop-dump/6', 'schema_version': 6})
        self.assertEqual(json.loads(files['backdrops.json']), doc)
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo = Path(scratch)
            target = bundle.save_bundle(manifest, files, repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), repo), target)
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), files['backdrops.json'])
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), files['backdrops.json'])
            wrong = copy.deepcopy(doc)
            wrong['frames'][1]['object_lists'][0]['objects'][1]['backdrop']['placement_refresh_inputs']['writes'][0]['written_unsigned'] ^= 1
            different_files = dict(files, **{'backdrops.json': bundle.json_bytes(wrong)})
            different_manifest = copy.deepcopy(manifest)
            for item in different_manifest['files']:
                if item['file'] == 'backdrops.json':
                    item.update(bytes=len(different_files['backdrops.json']), sha256=hashlib.sha256(different_files['backdrops.json']).hexdigest())
            different_files['manifest.json'] = bundle.json_bytes(different_manifest)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(different_manifest, different_files, repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()}, files)

    def test_late_invalid_fill_before_standalone_bundle_output_or_reporting(self):
        raw = combined_project()[0].replace(header(1, image=5), refresh_header(fill=3))
        for module, save in ((backdrop, 'save_backdrops'), (bundle, 'save_bundle')):
            stderr = io.StringIO()
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=raw), patch.object(module, save) as write, \
                    patch.object(project, 'report_fault') as report, redirect_stderr(stderr):
                self.assertEqual(module.main(), 2)
                self.assertIn('unsupported quick backdrop fill flags', stderr.getvalue())
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_absolute_source_spans_all_refresh_inputs(self):
        path = Path(os.environ['FF_TEST_PROJECT']); raw = path.read_bytes()
        doc = backdrop.backdrop_document(self.reader, raw); game = self.reader.read(raw)
        lists = [(s.data, s.offset+6, out['objects'], True) for s, out in zip(
            [s for s in game.segments if s.ident == 6], doc['global_object_lists'])]
        for level, frame in zip(game.levels(), doc['frames']):
            lists += [(b.data, level.offset+6+b.offset+6, out['objects'], False) for b, out in zip(
                [b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2], frame['object_lists'])]
        counts = {0:0, 1:0}
        for data, absolute, outputs, globals_ in lists:
            for obj, out in zip(self.reader.object_definitions(data, globals_have_blocks=globals_), outputs):
                if obj.object_type not in counts:
                    self.assertIsNone(out['backdrop']); continue
                counts[obj.object_type] += 1
                head = raw[absolute+obj.base:absolute+obj.base+68]
                self.assertEqual(head, data[obj.base:obj.base+68])
                ann = out['backdrop']['placement_refresh_inputs']
                self.assertEqual(ann['writes'], expected_writes(head))
                self.assertFalse(ann['runtime_resolution'])
        self.assertEqual(counts, {0:58, 1:352})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(backdrop.backdrop_document(self.reader, raw), doc)


if __name__ == '__main__':
    unittest.main()
