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
from test_placement_object_probes import synthetic_probes


def record(x, y):
    return struct.pack('<Hhh', 0x1234, x, y) + bytes(range(6, 32))


def decoded(records, pointers=None):
    pointers = [32 * i for i in range(len(records))] if pointers is None else pointers
    raw = placement_block(pointers, b''.join(records))
    return raw, layout.decode_placements(raw)


class CoordinateTests(unittest.TestCase):
    def test_signed_boundaries_axes_opaque_neighbours_and_source_preserved(self):
        values = [(0x8000, -32768), (0x8001, -32767), (0xffff, -1),
                  (0, 0), (1, 1), (0x7ffe, 32766), (0x7fff, 32767)]
        for xb, x in values:
            for yb, y in values:
                with self.subTest(x=x, y=y):
                    raw, block = decoded([record(x, y)])
                    before = copy.deepcopy(block)
                    layout.annotate_coordinate_inputs([block])
                    coordinates = block['records'][0].pop('coordinate_inputs')
                    self.assertEqual(coordinates['x'], {'record_offset': 2, 'raw_u16': xb, 'signed_i16': x})
                    self.assertEqual(coordinates['y'], {'record_offset': 4, 'raw_u16': yb, 'signed_i16': y})
                    self.assertEqual(block, before)
                    self.assertEqual(reconstruct(block), raw)

    def test_override_sentinel_is_not_a_record_sentinel_or_resolved_spawn(self):
        raw, block = decoded([record(-32768, -32768), record(-7, 13)])
        layout.annotate_coordinate_inputs([block])
        for rec in block['records']:
            inputs = rec['coordinate_inputs']
            self.assertEqual(inputs['meaning'], 'creation_coordinate_inputs')
            self.assertEqual(inputs['evidence'], 'original_runtime_creation_coordinate_branch')
            self.assertEqual(inputs['use_record_when_override_raw_u16'], 0x8000)
            self.assertFalse(inputs['runtime_resolution'])
            self.assertEqual(rec['meaning'], 'unknown')
        # 0x8000 stored in the record is an ordinary signed view, not omission.
        self.assertEqual(block['records'][0]['coordinate_inputs']['x']['signed_i16'], -32768)
        self.assertEqual(reconstruct(block), raw)

    def test_reversed_pointer_order_aliases_gaps_empty_and_repeated_blocks(self):
        raw, a = decoded([record(-7, 13), record(19, -23)], [32, layout.UNUSED, 0, 32])
        _, empty = decoded([], [layout.UNUSED])
        _, repeated = decoded([record(-1, 0)])
        layout.annotate_coordinate_inputs([a, empty, repeated])
        self.assertEqual([r['coordinate_inputs']['x']['signed_i16'] for r in a['records']], [-7, 19])
        self.assertEqual([r['coordinate_inputs']['y']['signed_i16'] for r in a['records']], [13, -23])
        self.assertEqual([s['record_id'] for s in a['slots']], [1, None, 0, 1])
        self.assertEqual(len(a['records']), 2)
        self.assertEqual(empty['records'], [])
        self.assertEqual(repeated['records'][0]['coordinate_inputs']['x']['raw_u16'], 0xffff)
        self.assertEqual(reconstruct(a), raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class CoordinateContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_both_frame_header_shapes_missing_empty_and_repeated_blocks(self):
        raw = synthetic_layout()
        doc = layout.layout_document(self.reader, raw)
        self.assertEqual((doc['schema_version'], doc['exporter']), (3, 'frame-layout/3'))
        self.assertTrue(doc['coverage']['placement_coordinate_inputs'])
        for key in ('placement_semantics', 'arena_geometry', 'spawns', 'behaviour'):
            self.assertFalse(doc['coverage'][key])
        self.assertEqual([f['header_bytes'] for f in doc['frames']], [0xb8, 0x78])
        self.assertEqual(doc['frames'][0]['placements'], [])
        placements = doc['frames'][1]['placements']
        self.assertEqual(placements[1]['records'], [])
        self.assertEqual(placements[0]['records'][0]['coordinate_inputs']['x']['raw_u16'], 0x0302)
        self.assertEqual(placements[0]['records'][1]['coordinate_inputs']['y']['signed_i16'], -1285)
        self.assertEqual(raw, synthetic_layout())
        self.assertEqual(doc, layout.layout_document(self.reader, raw))

    def test_object_probes_unchanged_and_json_contains_signed_inputs(self):
        raw, original_block = synthetic_probes()
        doc = layout.layout_document(self.reader, raw)
        for frame in doc['frames']:
            block = frame['placements'][0]
            self.assertEqual(reconstruct(block), original_block)
            for rec in block['records']:
                self.assertEqual(rec['object_slot_probe']['word_raw_u16'], int.from_bytes(bytes.fromhex(rec['raw_hex'])[:2], 'little'))
                self.assertFalse(rec['object_slot_probe']['runtime_resolution'])
                self.assertFalse(rec['coordinate_inputs']['runtime_resolution'])
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            out = layout.save_layout(doc, Path(scratch))
            saved = out.read_bytes()
            self.assertEqual(json.loads(saved), doc)
            self.assertEqual(layout.save_layout(doc, Path(scratch)).read_bytes(), saved)

    def test_bundle_component_and_immutable_repeats(self):
        raw, _ = synthetic_probes()
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(manifest['components']['frame-layout.json'], {'exporter': 'frame-layout/3', 'schema_version': 3})
        self.assertEqual(json.loads(files['frame-layout.json']), layout.layout_document(self.reader, raw))
        self.assertFalse(manifest['coverage']['arena_geometry'])
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch)), target)
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, files)

    def test_late_short_record_precedes_standalone_bundle_writes_and_reporting(self):
        raw = synthetic_layout()
        bad = raw[:-2] + struct.pack('<H', 1) + struct.pack('<I', 0) + bytes(31)
        # Keep the container extent valid; only the final placement is malformed.
        bad = bytearray(bad)
        struct.pack_into('<I', bad, len(raw) - 6, 37)
        last = self.reader.read(raw).levels()[-1]
        struct.pack_into('<I', bad, last.offset + 2, len(last.data) + 35)
        project.inventory(self.reader, bytes(bad))
        with self.assertRaisesRegex(project.InputError, 'unsupported placement record size'):
            layout.layout_document(self.reader, bytes(bad))
        for module, save in ((layout, 'save_layout'), (bundle, 'save_bundle')):
            with self.subTest(module=module.VERSION), \
                    patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path, 'read_bytes', return_value=bytes(bad)), \
                    patch.object(module, save) as write, patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_spans_signed_words_and_lossless_reconstruction(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = layout.layout_document(self.reader, raw)
        counts = []
        negatives = [0, 0]
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            _, blocks = self.reader.level_blocks(level.data)
            for block in frame['placements']:
                source = blocks[block['block_id']].data
                self.assertEqual(reconstruct(block), source)
                for rec in block['records']:
                    # Traverse the source table independently, never use an
                    # annotation offset as the expected byte-field position.
                    head = int.from_bytes(source[:2], 'little') * 4 + 2 + rec['id'] * 32
                    self.assertEqual(bytes.fromhex(rec['raw_hex']), source[head:head + 32])
                    for axis, at, index in (('x', head + 2, 0), ('y', head + 4, 1)):
                        bits = int.from_bytes(source[at:at + 2], 'little')
                        signed = bits if bits < 32768 else bits - 65536
                        self.assertEqual(rec['coordinate_inputs'][axis]['raw_u16'], bits)
                        self.assertEqual(rec['coordinate_inputs'][axis]['signed_i16'], signed)
                        negatives[index] += signed < 0
                    self.assertFalse(rec['coordinate_inputs']['runtime_resolution'])
                counts.append(len(block['records']))
        self.assertEqual(counts, [3, 75, 805, 845, 732, 872, 878, 609, 689, 741, 817, 902])
        self.assertEqual(sum(counts), 7968)
        self.assertGreater(negatives[0], 0)
        self.assertGreater(negatives[1], 0)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), doc['source']['sha256'])
        self.assertEqual(layout.layout_document(self.reader, raw), doc)


if __name__ == '__main__':
    unittest.main()
