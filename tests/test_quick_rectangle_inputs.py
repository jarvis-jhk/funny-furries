import copy
from contextlib import redirect_stderr
import io
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import backdrop_dump as backdrop, export_project as bundle, project_index as project
from test_backdrop_placement_probes import definitions, record, synthetic
from test_backdrop_refresh import refresh_header
from test_backdrop_dump import header
from test_frame_layout import placement_block


def coordinates(slot=0, x=65529, y=23):
    raw = bytearray(record(slot))
    struct.pack_into('<HH', raw, 2, x, y)
    return bytes(raw)


def sized_header(width=29, height=65525, **kwargs):
    raw = bytearray(refresh_header(**kwargs))
    struct.pack_into('<HH', raw, 34, width, height)
    return bytes(raw)


def signed(word):
    return word if word < 32768 else word - 65536


def assert_inputs(test, out, stored, head):
    # Read source and definition bytes independently of production refreshes.
    words = {'x': int.from_bytes(stored[2:4], 'little'),
             'y': int.from_bytes(stored[4:6], 'little'),
             'width': int.from_bytes(head[34:36], 'little'),
             'height': int.from_bytes(head[36:38], 'little')}
    offsets = {'x': 2, 'y': 4, 'width': 26, 'height': 28}
    test.assertEqual(out['fields'], {k: {'record_offset': offsets[k],
        'raw_u16': v, 'signed_i16': signed(v)} for k, v in words.items()})
    x, y, w, h = (signed(words[k]) for k in ('x', 'y', 'width', 'height'))
    test.assertEqual(out['zero_translation_edges'], {'left': x, 'top': y,
        'right_exclusive': x+w, 'bottom_exclusive': y+h})
    test.assertEqual(out['translation_inputs'], {
        'x': {'runtime_word_address': '0x41d662', 'signed_i16': None},
        'y': {'runtime_word_address': '0x41d664', 'signed_i16': None}})
    test.assertEqual(out['origin_rule'], 'signed_record_coordinate - signed_runtime_translation')
    test.assertEqual(out['exclusive_endpoint_rule'], 'origin + signed_refreshed_dimension')
    test.assertFalse(out['runtime_resolution'])


class QuickRectangleTests(unittest.TestCase):
    def test_signed_asymmetric_boundaries_zero_negative_no_normalization(self):
        boundaries = (0, 1, 32767, 32768, 32769, 65534, 65535)
        for x in boundaries:
            for width in boundaries:
                with self.subTest(x=x, width=width):
                    raw = bytearray(coordinates(x=x, y=65529))
                    struct.pack_into('<HH', raw, 26, width, 23)
                    out = backdrop.quick_rectangle_inputs(raw)
                    assert_inputs(self, out, raw, sized_header(width, 23))
                    self.assertEqual(out['zero_translation_edges']['right_exclusive'], signed(x)+signed(width))
        raw = bytearray(coordinates(x=32768, y=32767))
        struct.pack_into('<HH', raw, 26, 32768, 32767)
        out = backdrop.quick_rectangle_inputs(raw)
        self.assertEqual(out['zero_translation_edges'], {
            'left': -32768, 'top': 32767, 'right_exclusive': -65536, 'bottom_exclusive': 65534})

    def test_complete_record_required_opaque_neighbours_preserved(self):
        raw = bytearray(coordinates()); struct.pack_into('<HH', raw, 26, 29, 65525)
        out = backdrop.quick_rectangle_inputs(raw)
        copy_ = bytes(raw)
        for at in (0, 1, 6, 7, 8, 9, 12, 25, 30, 31):
            raw[at] ^= 255
        self.assertEqual(backdrop.quick_rectangle_inputs(raw), out)
        self.assertNotEqual(bytes(raw), copy_)
        for data in (b'', copy_[:-1], copy_+b'x'):
            with self.subTest(size=len(data)), self.assertRaisesRegex(project.InputError, 'complete placement record'):
                backdrop.quick_rectangle_inputs(data)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class QuickRectangleContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def document(self, heads, records):
        return backdrop.backdrop_document(self.reader, synthetic(self.reader, [[],
            [(2, definitions(heads)), (3, placement_block(list(range(0,len(records)*32,32)), b''.join(records)))]]))

    def test_quick_header_dimensions_ignore_old_record_type_and_dimensions(self):
        for fill in (0, 1, 2, 16, 17, 18):
            head = sized_header(fill=fill, high=255)
            raw = coordinates()
            doc = self.document([head], [raw])
            candidate = doc['frames'][1]['placement_refresh_probes'][0]['records'][0]['candidates'][0]
            ann = candidate['conditional_quick_rectangle_inputs']
            assert_inputs(self, ann, raw, head)
            self.assertNotEqual(raw[26:30], bytes.fromhex(candidate['conditional_record_hex'])[26:30])
            self.assertNotEqual(raw[6], 0)
            self.assertTrue(doc['coverage']['conditional_quick_rectangle_inputs'])
            for name in ('runtime_rendering', 'global_reference_resolution', 'arena_geometry', 'spawns', 'behaviour'):
                self.assertFalse(doc['coverage'][name])

    def test_local_ambiguity_ordinary_deleted_missing_no_global_fallback(self):
        a = sized_header(29, 65525)
        b = bytearray(sized_header(7, 41)); b[38] = 0; b = bytes(b)
        raw = synthetic(self.reader, [[(2, definitions([sized_header(33,44)]))],
            [(2, definitions([a])), (2, definitions([b])), (2, definitions([refresh_header(1)])),
             (2, definitions([header(255), header(2)])), (3, placement_block([0,32,64],
                 coordinates()+coordinates(1)+coordinates(65535))) ]])
        doc = backdrop.backdrop_document(self.reader, raw)
        records = doc['frames'][1]['placement_refresh_probes'][0]['records']
        candidates = records[0]['candidates']
        self.assertEqual(records[0]['status'], 'multiple_local_candidates')
        self.assertEqual([c['global'] for c in candidates], [True,False,True,True])
        for c,h in zip(candidates[:2], (a,b)):
            assert_inputs(self, c['conditional_quick_rectangle_inputs'], coordinates(), h)
        self.assertNotEqual(candidates[0]['conditional_quick_rectangle_inputs'], candidates[1]['conditional_quick_rectangle_inputs'])
        for c in candidates[2:] + records[1]['candidates']:
            self.assertIsNone(c['conditional_quick_rectangle_inputs'])
        self.assertEqual(records[2]['candidates'], [])

    def test_aliases_reversed_pointer_order_and_empty_repeated_blocks(self):
        head = sized_header()
        raw = synthetic(self.reader, [[], [(2, definitions([head])),
            (3, placement_block([32,0xFFFFFFFF,0,32], coordinates()+coordinates(x=32768,y=32767))),
            (3, placement_block([],b'')), (3, placement_block([0],coordinates(x=65535,y=0))) ]])
        doc = backdrop.backdrop_document(self.reader,raw)
        self.assertEqual(doc['frames'][0]['placement_refresh_probes'], [])
        blocks = doc['frames'][1]['placement_refresh_probes']
        self.assertEqual([s['record_id'] for s in blocks[0]['slots']], [1,None,0,1])
        for out, stored in zip(blocks[0]['records'], (coordinates(),coordinates(x=32768,y=32767))):
            assert_inputs(self, out['candidates'][0]['conditional_quick_rectangle_inputs'],stored,head)
        self.assertEqual(blocks[1]['records'], [])
        assert_inputs(self, blocks[2]['records'][0]['candidates'][0]['conditional_quick_rectangle_inputs'],coordinates(x=65535,y=0),head)

    def test_bundle_repeat_standalone_and_immutable_refusal(self):
        raw = synthetic(self.reader,[[], [(2,definitions([sized_header()])),(3,placement_block([0],coordinates()))]])
        doc = backdrop.backdrop_document(self.reader,raw)
        manifest,files = bundle.research_bundle(self.reader,raw)
        self.assertEqual(json.loads(files['backdrops.json']),doc)
        self.assertEqual(manifest['components']['backdrops.json'], {'exporter':'backdrop-dump/9','schema_version':9})
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo=Path(scratch);target=bundle.save_bundle(manifest,files,repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader,raw),repo),target)
            self.assertEqual(backdrop.save_backdrops(doc,repo).read_bytes(),files['backdrops.json'])
            old=copy.deepcopy(doc)
            for frame in old['frames']:
                for block in frame['placement_refresh_probes']:
                    for r in block['records']:
                        for c in r['candidates']:
                            c.pop('conditional_quick_rectangle_inputs')
                            c.pop('conditional_quick_fill_inputs')
            old['coverage'].pop('conditional_quick_fill_inputs');old['coverage'].pop('conditional_quick_rectangle_inputs');old['schema_version']=5;old['exporter']='backdrop-dump/5'
            different=dict(files,**{'backdrops.json':bundle.json_bytes(old)})
            old_manifest=copy.deepcopy(manifest)
            old_manifest['components']['backdrops.json']={'exporter':'backdrop-dump/5','schema_version':5}
            for item in old_manifest['files']:
                if item['file']=='backdrops.json':
                    item.update(bytes=len(different['backdrops.json']),sha256=hashlib.sha256(different['backdrops.json']).hexdigest())
            different['manifest.json']=bundle.json_bytes(old_manifest)
            with self.assertRaisesRegex(project.InputError,'existing research bundle differs'):
                bundle.save_bundle(old_manifest,different,repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},files)

    def test_late_bad_header_before_standalone_bundle_output_or_reporting(self):
        raw = synthetic(self.reader,[[],[(2,definitions([sized_header(),refresh_header(fill=3)])),
            (3,placement_block([0,32],coordinates()+coordinates(1))) ]])
        for module,save in ((backdrop,'save_backdrops'),(bundle,'save_bundle')):
            stderr=io.StringIO()
            with self.subTest(module=module.VERSION), patch.object(module.sys,'argv',['export','unused','--klikback-src',os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path,'read_bytes',return_value=raw), patch.object(module,save) as write, \
                    patch.object(project,'report_fault') as report, redirect_stderr(stderr):
                self.assertEqual(module.main(),2)
                self.assertIn('unsupported quick backdrop fill flags',stderr.getvalue())
                write.assert_not_called();report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_coordinate_header_spans_all_quick_candidates(self):
        path=Path(os.environ['FF_TEST_PROJECT']);raw=path.read_bytes()
        doc=backdrop.backdrop_document(self.reader,raw);game=self.reader.read(raw)
        counts={'quick':0,'other':0}
        for level,frame in zip(game.levels(),doc['frames']):
            blocks=self.reader.level_blocks(level.data)[1]
            for out in frame['placement_refresh_probes']:
                p=blocks[out['block_id']];n=int.from_bytes(p.data[:2],'little')
                absolute=level.offset+6+p.offset+6+2+4*n
                for r in out['records']:
                    data=raw[absolute+r['id']*32:absolute+(r['id']+1)*32]
                    for c in r['candidates']:
                        if c['type']!=0 or c['deleted']:
                            self.assertIsNone(c['conditional_quick_rectangle_inputs']);counts['other']+=1;continue
                        definition=blocks[c['definition_block_id']]
                        matches=[o for o in self.reader.object_definitions(definition.data) if o.index==int.from_bytes(data[:2],'little')]
                        self.assertEqual(len(matches),1)
                        at=level.offset+6+definition.offset+6+matches[0].base
                        head=raw[at:at+68]
                        assert_inputs(self,c['conditional_quick_rectangle_inputs'],data,head);counts['quick']+=1
        self.assertEqual(counts['quick'],69)
        self.assertGreater(counts['other'],0)
        self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(backdrop.backdrop_document(self.reader,raw),doc)


if __name__=='__main__':
    unittest.main()
