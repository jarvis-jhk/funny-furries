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
from test_frame_layout import placement_block, reconstruct, synthetic_layout
from test_placement_object_probes import obj, synthetic_probes


def record(slot, word):
    raw = bytearray(range(32))
    struct.pack_into('<H', raw, 0, slot)
    struct.pack_into('<H', raw, 6, word)
    return bytes(raw)


def decoded(records, lists=(), pointers=None):
    pointers = [32 * i for i in range(len(records))] if pointers is None else pointers
    raw = placement_block(pointers, b''.join(records))
    block = layout.decode_placements(raw)
    layout.annotate_object_slot_probes([block], lists)
    layout.annotate_coordinate_inputs([block])
    return raw, block


class TypeTests(unittest.TestCase):
    def test_all_low_bytes_high_bits_and_opaque_neighbours_preserved(self):
        for high in (0, 1, 4, 5, 0x7f, 0x80, 0xff):
            raw, block = decoded([record(0x1234, high * 256 + low) for low in range(256)])
            before = copy.deepcopy(block)
            layout.annotate_creation_types([block])
            for low, rec in enumerate(block['records']):
                ann = rec.pop('creation_type_input')
                self.assertEqual((ann['raw_u16'], ann['type_raw_u8'], ann['opaque_high_u8']),
                                 (high * 256 + low, low, high))
                self.assertEqual(ann['record_offset'], 6)
                self.assertFalse(ann['runtime_resolution'])
            self.assertEqual(block, before)
            self.assertEqual(reconstruct(block), raw)

    def test_comparisons_preserve_missing_deleted_mismatch_and_ambiguity(self):
        cases = [((), []), ([(4, [obj(3, deleted=True)])], [(4, 2, True, True)]),
                 ([(4, [obj(3, type=7)])], [(4, 7, False, False)]),
                 ([(4, [obj(3, type=2)]), (9, [obj(3, type=7, deleted=True)])],
                  [(4, 2, False, True), (9, 7, True, False)])]
        for lists, expected in cases:
            with self.subTest(expected=expected):
                raw, block = decoded([record(3, 0x8102)], lists)
                before = copy.deepcopy(block)
                old_lists = copy.deepcopy(lists)
                layout.annotate_creation_types([block])
                ann = block['records'][0].pop('creation_type_input')
                self.assertEqual([(c['block_id'], c['type'], c['deleted'], c['type_equal'])
                                  for c in ann['local_definition_comparisons']], expected)
                self.assertTrue(all(c['id'] == 3 for c in ann['local_definition_comparisons']))
                self.assertEqual(block, before)
                self.assertEqual(lists, old_lists)
                self.assertEqual(reconstruct(block), raw)

    def test_type_boundaries_have_no_guessed_deleted_extension_or_sentinel_rules(self):
        words = [0, 1, 2, 31, 32, 255, 256, 257, 1024, 1280, 0x8000, 0xffff]
        raw, block = decoded([record(0xffff, w) for w in words])
        layout.annotate_creation_types([block])
        for word, rec in zip(words, block['records']):
            ann = rec['creation_type_input']
            self.assertEqual(ann['type_raw_u8'], word % 256)
            self.assertEqual(ann['meaning'], 'creation_type_input')
            self.assertEqual(ann['evidence'], 'original_runtime_creation_type_dispatch')
            self.assertEqual(ann['local_definition_comparisons'], [])
            self.assertEqual(rec['meaning'], 'unknown')
            self.assertFalse(ann['runtime_resolution'])
        self.assertEqual(reconstruct(block), raw)

    def test_aliases_reversed_pointers_gaps_empty_and_repeated_blocks(self):
        raw, first = decoded([record(3, 257), record(5, 0x8007)], [(8, [obj(3, type=1), obj(5, type=7)])],
                             [32, layout.UNUSED, 0, 32])
        _, empty = decoded([], pointers=[layout.UNUSED])
        _, repeated = decoded([record(3, 2)], [(12, [obj(3, type=2)])])
        layout.annotate_creation_types([first, empty, repeated])
        self.assertEqual([r['creation_type_input']['type_raw_u8'] for r in first['records']], [1, 7])
        self.assertEqual([s['record_id'] for s in first['slots']], [1, None, 0, 1])
        self.assertEqual(empty['records'], [])
        self.assertEqual(repeated['records'][0]['creation_type_input']['local_definition_comparisons'][0]['block_id'], 12)
        self.assertEqual(reconstruct(first), raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class TypeContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_scope_candidates_header_shapes_and_existing_fields(self):
        raw, original_block = synthetic_probes()
        doc = layout.layout_document(self.reader, raw)
        self.assertEqual((doc['schema_version'], doc['exporter']), (5, 'frame-layout/5'))
        self.assertTrue(doc['coverage']['placement_creation_type_inputs'])
        for key in ('placement_semantics', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][key])
        for frame in doc['frames']:
            block = frame['placements'][0]
            self.assertEqual(reconstruct(block), original_block)
            for rec in block['records']:
                ann = rec['creation_type_input']
                self.assertEqual(ann['type_raw_u8'], 6)
                expected = [{**{k: c[k] for k in ('block_id', 'id', 'type', 'deleted')},
                             'type_equal': c['type'] == 6} for c in rec['object_slot_probe']['candidates']]
                self.assertEqual(ann['local_definition_comparisons'], expected)
                self.assertFalse(rec['coordinate_inputs']['runtime_resolution'])
        header_doc = layout.layout_document(self.reader, synthetic_layout())
        self.assertEqual([f['header_bytes'] for f in header_doc['frames']], [0xb8, 0x78])
        self.assertEqual(header_doc['frames'][0]['placements'], [])
        self.assertEqual(header_doc['frames'][1]['placements'][1]['records'], [])
        self.assertEqual(layout.layout_document(self.reader, raw), doc)

    def test_bundle_component_and_standalone_immutable_repeats(self):
        raw, _ = synthetic_probes()
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
            self.assertEqual(before, files)
            single = layout.save_layout(doc, Path(scratch))
            self.assertEqual(single.read_bytes(), files['frame-layout.json'])
            self.assertEqual(layout.save_layout(doc, Path(scratch)).read_bytes(), single.read_bytes())
            changed = copy.deepcopy(doc)
            changed['frames'][0]['placements'][0]['records'][0]['creation_type_input']['type_raw_u8'] ^= 1
            changed_files = dict(files, **{'frame-layout.json': bundle.json_bytes(changed)})
            changed_manifest = copy.deepcopy(manifest)
            for entry in changed_manifest['files']:
                if entry['file'] == 'frame-layout.json':
                    entry['bytes'] = len(changed_files[entry['file']])
                    entry['sha256'] = hashlib.sha256(changed_files[entry['file']]).hexdigest()
            changed_files['manifest.json'] = bundle.json_bytes(changed_manifest)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(changed_manifest, changed_files, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_late_malformed_block_precedes_annotations_writes_and_reporting(self):
        raw = synthetic_layout()
        bad = raw[:-2] + struct.pack('<H', 1)
        for module, save in ((layout, 'save_layout'), (bundle, 'save_bundle')):
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(layout, 'annotate_creation_types', wraps=layout.annotate_creation_types) as annotate, \
                    patch.object(module, save) as write, patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                self.assertEqual(annotate.call_count, 1)  # first valid empty frame only
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_source_words_and_independent_local_header_comparisons(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = layout.layout_document(self.reader, raw)
        count = nonzero_high = 0
        types = set()
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            _, blocks = self.reader.level_blocks(level.data)
            lists = [(i, self.reader.object_definitions(b.data)) for i, b in enumerate(blocks) if b.ident == 2]
            for block in frame['placements']:
                source = blocks[block['block_id']].data
                self.assertEqual(reconstruct(block), source)
                start = int.from_bytes(source[:2], 'little') * 4 + 2
                for rec in block['records']:
                    at = start + rec['id'] * 32
                    self.assertEqual(bytes.fromhex(rec['raw_hex']), source[at:at + 32])
                    word = int.from_bytes(source[at + 6:at + 8], 'little')
                    slot = int.from_bytes(source[at:at + 2], 'little')
                    expected = [{'block_id': i, 'id': o.index, 'type': o.object_type, 'deleted': o.deleted,
                                 'type_equal': o.object_type == (word & 255)}
                                for i, entries in lists for o in entries if o.index == slot]
                    ann = rec['creation_type_input']
                    self.assertEqual((ann['raw_u16'], ann['type_raw_u8'], ann['opaque_high_u8']), (word, word & 255, word >> 8))
                    self.assertEqual(ann['local_definition_comparisons'], expected)
                    self.assertEqual(len(expected), 1)
                    self.assertTrue(expected[0]['type_equal'])
                    self.assertFalse(expected[0]['deleted'])
                    self.assertFalse(ann['runtime_resolution'])
                    count += 1
                    nonzero_high += bool(word >> 8)
                    types.add(word & 255)
        self.assertEqual(count, 7968)
        self.assertEqual(nonzero_high, 1722)
        self.assertEqual(types, {0, 1, 2, 5, 6, 7, 32, 33, 34})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(doc, layout.layout_document(self.reader, raw))


if __name__ == '__main__':
    unittest.main()
