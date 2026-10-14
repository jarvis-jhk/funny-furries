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

from tools import backdrop_dump as backdrop, export_project as bundle, image_dump as image, project_index as project
from test_backdrop_dump import header, project_bytes
from test_export_project import combined_project
from test_image_dump import record, read_png


class ImageDimensionTests(unittest.TestCase):
    def test_metadata_boundaries_opaque_modes_and_no_pixel_or_runtime_claim(self):
        for w in (0, 1, 32767, 32768, 32769, 65534, 65535):
            for h in (0, 1, 32767, 32768, 32769, 65534, 65535):
                # A header-only record deliberately has no valid PNG pixels.
                raw = bytearray(range(24))
                struct.pack_into('<IHH', raw, 6, 0, w, h)
                out = backdrop.image_dimension_candidate(bytes(raw), 11, 5, 52)
                self.assertEqual(out['width']['raw_u16'], w)
                self.assertEqual(out['height']['raw_u16'], h)
                self.assertEqual(bytes.fromhex(out['header_hex']), bytes(raw))
                self.assertEqual(out['record_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual((out['segment_id'], out['image_id'], out['bank_offset'], out['record_bytes']), (11, 5, 52, 24))
                self.assertEqual(out['width']['image_record_offset'], 10)
                self.assertEqual(out['height']['image_record_offset'], 12)
                self.assertNotIn('signed_i16', out['width'])
                self.assertNotIn('world_bounds', out)

    def test_short_and_length_mismatch_refused(self):
        for raw in (b'', bytes(23), record()[:-1], record()+b'x'):
            with self.subTest(length=len(raw)), self.assertRaises(project.InputError):
                backdrop.image_dimension_candidate(raw, 1, 5, 12)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ImageDimensionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_bank_slot_identity_not_internal_image_word(self):
        raw = project_bytes([header(1, image=5)])
        doc = backdrop.backdrop_document(self.reader, raw)
        ann = doc['frames'][1]['object_lists'][1]['objects'][0]['backdrop']['ordinary_backdrop_image_candidates']
        self.assertEqual(ann['status'], 'single_bank_candidate')
        self.assertEqual(ann['meaning'], 'ordinary_backdrop_image_dimension_candidates')
        self.assertEqual(ann['evidence'], 'stored_image_metadata')
        self.assertFalse(ann['runtime_resolution'])
        candidate = ann['candidates'][0]
        self.assertEqual(candidate['image_id'], 5)
        self.assertEqual(int.from_bytes(bytes.fromhex(candidate['header_hex'])[:2], 'little'), 13)
        self.assertEqual((candidate['width']['raw_u16'], candidate['height']['raw_u16']), (3, 2))
        self.assertTrue(doc['coverage']['ordinary_backdrop_image_dimension_candidates'])
        for key in ('runtime_rendering', 'global_reference_resolution', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][key])

    def test_duplicate_banks_keep_conflicting_sizes_and_local_global_handles(self):
        raw = bytearray(project_bytes([header(1, image=5), header(fill=1, image=5), header(255)], repeated=True))
        banks = [s for s in self.reader.read(raw).segments if s.ident == 10]
        second = banks[2]
        offset = next(at for slot, at, _ in self.reader.walk_bank(second.data) if slot == 5)
        struct.pack_into('<HH', raw, second.offset+6+offset+10, 65529, 32768)
        doc = backdrop.backdrop_document(self.reader, bytes(raw))
        objects = doc['frames'][1]['object_lists'][1]['objects']
        ann = objects[0]['backdrop']['ordinary_backdrop_image_candidates']
        self.assertEqual(ann['status'], 'multiple_bank_candidates')
        self.assertEqual([c['segment_id'] for c in ann['candidates']], objects[0]['backdrop']['artwork']['image_bank_candidates'])
        self.assertEqual([(c['width']['raw_u16'], c['height']['raw_u16']) for c in ann['candidates']], [(3, 2), (65529, 32768)])
        self.assertTrue(objects[0]['global'])
        global_ann = doc['global_object_lists'][0]['objects'][0]['backdrop']['ordinary_backdrop_image_candidates']
        self.assertEqual([c['image_id'] for c in global_ann['candidates']], [2, 2])
        self.assertEqual([(c['width']['raw_u16'], c['height']['raw_u16']) for c in global_ann['candidates']], [(3, 2), (3, 2)])
        self.assertIsNone(objects[1]['backdrop']['ordinary_backdrop_image_candidates'])
        self.assertIsNone(objects[2]['backdrop'])
        self.assertEqual(backdrop.backdrop_document(self.reader, bytes(raw)), doc)

    def test_unused_and_mosaic_metadata_not_promoted_to_ordinary_dimensions(self):
        raw = project_bytes([header(fill=1, image=5)], image_records={2: record(), 5: b'x'})
        doc = backdrop.backdrop_document(self.reader, raw)
        quick = doc['frames'][1]['object_lists'][1]['objects'][0]['backdrop']
        self.assertIsNone(quick['ordinary_backdrop_image_candidates'])
        self.assertEqual(quick['artwork']['image_id'], 5)
        self.assertIsNotNone(quick['quick_backdrop_dimension_inputs'])

    def test_standalone_bundle_png_agreement_repeats_and_immutable_difference(self):
        raw = combined_project()[0]
        doc = backdrop.backdrop_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(json.loads(files['backdrops.json']), doc)
        self.assertEqual(manifest['components']['backdrops.json'], {'exporter': 'backdrop-dump/4', 'schema_version': 4})
        ann = doc['frames'][1]['object_lists'][0]['objects'][1]['backdrop']['ordinary_backdrop_image_candidates']
        candidate = ann['candidates'][0]
        png = files[f"image-{candidate['segment_id']}-{candidate['image_id']}.png"]
        self.assertEqual(read_png(png)[:2], (candidate['width']['raw_u16'], candidate['height']['raw_u16']))
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo = Path(scratch)
            target = bundle.save_bundle(manifest, files, repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), repo), target)
            standalone = backdrop.save_backdrops(doc, repo)
            self.assertEqual(standalone.read_bytes(), files['backdrops.json'])
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), standalone.read_bytes())
            wrong = copy.deepcopy(doc)
            wrong['frames'][1]['object_lists'][0]['objects'][1]['backdrop']['ordinary_backdrop_image_candidates']['candidates'][0]['width']['raw_u16'] += 1
            wrong_files = dict(files, **{'backdrops.json': bundle.json_bytes(wrong)})
            wrong_manifest = copy.deepcopy(manifest)
            for entry in wrong_manifest['files']:
                if entry['file'] == 'backdrops.json':
                    entry.update(bytes=len(wrong_files['backdrops.json']), sha256=hashlib.sha256(wrong_files['backdrops.json']).hexdigest())
            wrong_files['manifest.json'] = bundle.json_bytes(wrong_manifest)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(wrong_manifest, wrong_files, repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()}, files)

    def test_late_bad_referenced_metadata_before_standalone_bundle_or_reporting(self):
        for bad in (b'x', record()[:-1]):
            raw = project_bytes([header(1, image=5)], image_records={2: record(), 5: bad})
            for module, save in ((backdrop, 'save_backdrops'), (bundle, 'save_bundle')):
                stderr = io.StringIO()
                with self.subTest(length=len(bad), module=module.VERSION), \
                        patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                        patch.object(Path, 'read_bytes', return_value=raw), \
                        patch.object(module, save) as write, patch.object(project, 'report_fault') as report, \
                        redirect_stderr(stderr):
                    self.assertEqual(module.main(), 2)
                    self.assertIn('backdrop image', stderr.getvalue())
                    write.assert_not_called()
                    report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_absolute_spans_bank_slots_and_independent_png_dimensions(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        doc = backdrop.backdrop_document(self.reader, raw)
        image_manifest, files = image.image_bundle(self.reader, raw)
        pngs = {(b['segment_id'], e['id']): read_png(files[e['file']])[:2]
                for b in image_manifest['banks'] for e in b['entries']}
        spans = {}
        for segment_id, segment in enumerate(game.segments):
            if segment.ident == 10:
                for slot, at, size in self.reader.walk_bank(segment.data):
                    spans[segment_id, slot] = (segment.offset+6+at, at, size)
        ordinary, quick = 0, 0
        for outputs in ([g['objects'] for g in doc['global_object_lists']] +
                        [b['objects'] for f in doc['frames'] for b in f['object_lists']]):
            for out in outputs:
                if out['type'] not in (0, 1):
                    continue
                ann = out['backdrop']['ordinary_backdrop_image_candidates']
                if out['type'] == 0:
                    quick += 1
                    self.assertIsNone(ann)
                    continue
                ordinary += 1
                self.assertFalse(ann['runtime_resolution'])
                self.assertEqual(ann['status'], 'single_bank_candidate')
                self.assertEqual(len(ann['candidates']), 1)
                candidate = ann['candidates'][0]
                key = candidate['segment_id'], out['backdrop']['image_word_raw_u16']
                at, bank_at, size = spans[key]
                record_bytes = raw[at:at+size]
                self.assertEqual(candidate['image_id'], key[1])
                self.assertEqual((candidate['bank_offset'], candidate['record_bytes']), (bank_at, size))
                self.assertEqual(bytes.fromhex(candidate['header_hex']), record_bytes[:24])
                self.assertEqual(candidate['record_sha256'], hashlib.sha256(record_bytes).hexdigest())
                pair = (int.from_bytes(raw[at+10:at+12], 'little'), int.from_bytes(raw[at+12:at+14], 'little'))
                self.assertEqual((candidate['width']['raw_u16'], candidate['height']['raw_u16']), pair)
                self.assertEqual(pngs[key], pair)
        self.assertEqual((ordinary, quick), (352, 58))
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
