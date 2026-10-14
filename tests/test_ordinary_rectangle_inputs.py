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
from test_backdrop_placement_probes import definitions, synthetic
from test_backdrop_refresh import refresh_header
from test_backdrop_dump import header, project_bytes
from test_frame_layout import placement_block
from test_quick_rectangle_inputs import coordinates, signed


def metadata(width, height, segment=12):
    raw = bytearray(range(24))
    struct.pack_into('<IHH', raw, 6, 0, width, height)
    return backdrop.image_dimension_candidate(bytes(raw), segment, 5, 52)


def assert_inputs(test, ann, stored, image_records):
    x, y = struct.unpack_from('<hh', stored, 2)
    test.assertEqual(ann['coordinates'], {
        axis: {'record_offset': at, 'raw_u16': int.from_bytes(stored[at:at+2], 'little'),
               'signed_i16': value} for axis, at, value in (('x',2,x), ('y',4,y))})
    test.assertFalse(ann['runtime_resolution']); test.assertFalse(ann['metadata_lookup_performed'])
    test.assertEqual(ann['metadata_result_inputs'], {
        'width': {'returned_buffer_offset':10, 'signed_i16':None},
        'height': {'returned_buffer_offset':12, 'signed_i16':None}})
    test.assertTrue(all(v['signed_i16'] is None for v in ann['translation_inputs'].values()))
    test.assertEqual(ann['exclusive_endpoint_rule'], 'origin + signed_returned_metadata_dimension')
    test.assertEqual(ann['candidate_assumption'], 'returned_dimension_words_equal_this_stored_image_candidate')
    test.assertEqual(len(ann['dimension_candidates']), len(image_records))
    for candidate, raw in zip(ann['dimension_candidates'], image_records):
        width, height = struct.unpack_from('<hh', raw, 10)
        for axis, at, value in (('width',10,width), ('height',12,height)):
            test.assertEqual(candidate['fields'][axis], {'image_record_offset':at,
                'raw_u16':int.from_bytes(raw[at:at+2],'little'), 'signed_i16':value})
        test.assertEqual(candidate['zero_translation_candidate_edges'], {
            'left':x, 'top':y, 'right_exclusive':x+width, 'bottom_exclusive':y+height})
        test.assertEqual(candidate['record_sha256'], hashlib.sha256(raw).hexdigest())


class OrdinaryRectangleTests(unittest.TestCase):
    def test_signed_metadata_boundaries_and_no_normalization(self):
        bounds = (0,1,32767,32768,32769,65534,65535)
        for x in bounds:
            for width in bounds:
                with self.subTest(x=x,width=width):
                    raw = coordinates(x=x,y=32767)
                    image = metadata(width,32768)
                    ann = backdrop.ordinary_rectangle_inputs(raw, {'status':'single_bank_candidate','candidates':[image]})
                    assert_inputs(self,ann,raw,[bytes.fromhex(image['header_hex'])])
                    self.assertEqual(ann['dimension_candidates'][0]['zero_translation_candidate_edges']['right_exclusive'],signed(x)+signed(width))

    def test_complete_record_and_opaque_stored_dimensions(self):
        raw = bytearray(coordinates())
        images = {'status':'multiple_bank_candidates','candidates':[metadata(3,2), metadata(65529,32768,14)]}
        out = backdrop.ordinary_rectangle_inputs(raw,images)
        original = bytes(raw)
        for at in (0,1,6,7,12,16,24,26,27,28,29,30,31): raw[at] ^= 255
        self.assertEqual(backdrop.ordinary_rectangle_inputs(raw,images),out)
        self.assertNotEqual(raw,original)
        self.assertEqual([c['segment_id'] for c in out['dimension_candidates']],[12,14])
        for bad in (b'',original[:-1],original+b'x'):
            with self.assertRaisesRegex(project.InputError,'complete placement record'):
                backdrop.ordinary_rectangle_inputs(bad,images)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class OrdinaryRectangleContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def make(self, frames, repeated=False):
        # Supply complete independent fixture banks, still parsed by the real reader.
        with patch('test_backdrop_placement_probes.project_bytes', return_value=project_bytes(repeated=repeated)):
            return synthetic(self.reader,frames)

    def test_conflicting_banks_local_handle_and_signed_image_candidates(self):
        head = refresh_header(1,255)
        raw = bytearray(self.make([[],[(2,definitions([head])),(3,placement_block([0],coordinates()))]],True))
        banks = [(i,s) for i,s in enumerate(self.reader.read(raw).segments) if s.ident==10]
        sid,bank = banks[-1]
        at = next(at for slot,at,_ in self.reader.walk_bank(bank.data) if slot==5)
        struct.pack_into('<HH',raw,bank.offset+6+at+10,65529,32768)
        banks = [(i,s) for i,s in enumerate(self.reader.read(raw).segments) if s.ident==10]
        doc = backdrop.backdrop_document(self.reader,bytes(raw))
        c = doc['frames'][1]['placement_refresh_probes'][0]['records'][0]['candidates'][0]
        ann = c['conditional_ordinary_rectangle_inputs']
        entries = [s.data[at:at+size] for _,s in banks for slot,at,size in self.reader.walk_bank(s.data) if slot==5]
        assert_inputs(self,ann,coordinates(),entries)
        self.assertEqual(ann['status'],'multiple_bank_candidates')
        self.assertEqual([v['image_id'] for v in ann['dimension_candidates']],[5,5])
        self.assertEqual(ann['image_word'],{'record_offset':8,'raw_u16':5})
        self.assertTrue(c['global'])
        self.assertEqual(doc['global_object_lists'][0]['objects'][0]['backdrop']['image_word_raw_u16'],2)
        self.assertTrue(doc['coverage']['conditional_ordinary_rectangle_inputs'])
        for key in ('runtime_rendering','global_reference_resolution','arena_geometry','spawns','behaviour'):
            self.assertFalse(doc['coverage'][key])

    def test_ambiguous_definitions_other_types_and_no_global_fallback(self):
        other = bytearray(refresh_header(1,image=2));other[38]=0
        raw = self.make([[(2,definitions([refresh_header(1)]))],
            [(2,definitions([refresh_header(1)])),(2,definitions([bytes(other)])),
             (2,definitions([refresh_header(0)])),(2,definitions([header(255),header(2)])),
             (3,placement_block([0,32,64],coordinates()+coordinates(1)+coordinates(65535))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        records=doc['frames'][1]['placement_refresh_probes'][0]['records'];candidates=records[0]['candidates']
        self.assertEqual([c['global'] for c in candidates],[True,False,True,True])
        self.assertEqual([c['conditional_ordinary_rectangle_inputs']['image_word']['raw_u16'] for c in candidates[:2]],[5,2])
        for c in candidates[2:]+records[1]['candidates']: self.assertIsNone(c['conditional_ordinary_rectangle_inputs'])
        self.assertEqual(records[2]['candidates'],[])
        self.assertIsNone(candidates[0]['conditional_quick_rectangle_inputs'])
        self.assertIsNotNone(candidates[2]['conditional_quick_rectangle_inputs'])

    def test_aliases_gaps_reverse_order_absent_empty_repeated_blocks(self):
        raw=self.make([[],[(2,definitions([refresh_header(1)])),
            (3,placement_block([32,0xffffffff,0,32],coordinates()+coordinates(x=32768,y=65535))),
            (3,placement_block([],b'')),(3,placement_block([0],coordinates(x=1,y=0))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        self.assertEqual(doc['frames'][0]['placement_refresh_probes'],[])
        blocks=doc['frames'][1]['placement_refresh_probes']
        self.assertEqual([s['record_id'] for s in blocks[0]['slots']],[1,None,0,1])
        self.assertEqual([r['candidates'][0]['conditional_ordinary_rectangle_inputs']['coordinates']['x']['signed_i16'] for r in blocks[0]['records']],[-7,-32768])
        self.assertEqual(blocks[1]['records'],[])
        self.assertEqual(blocks[2]['records'][0]['candidates'][0]['conditional_ordinary_rectangle_inputs']['coordinates']['x']['signed_i16'],1)

    def test_standalone_bundle_repeats_and_previous_immutable_refusal(self):
        raw=self.make([[],[(2,definitions([refresh_header(1)])),(3,placement_block([0],coordinates()))]])
        doc=backdrop.backdrop_document(self.reader,raw);manifest,files=bundle.research_bundle(self.reader,raw)
        self.assertEqual(json.loads(files['backdrops.json']),doc)
        self.assertEqual(manifest['components']['backdrops.json'],{'exporter':'backdrop-dump/9','schema_version':9})
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo=Path(scratch);target=bundle.save_bundle(manifest,files,repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader,raw),repo),target)
            self.assertEqual(backdrop.save_backdrops(doc,repo).read_bytes(),files['backdrops.json'])
            self.assertEqual(backdrop.save_backdrops(doc,repo).read_bytes(),files['backdrops.json'])
            old=copy.deepcopy(doc)
            for f in old['frames']:
                for b in f['placement_refresh_probes']:
                    for r in b['records']:
                        for c in r['candidates']: c.pop('conditional_ordinary_rectangle_inputs')
            old['coverage'].pop('conditional_ordinary_rectangle_inputs');old['schema_version']=7;old['exporter']='backdrop-dump/7'
            m=copy.deepcopy(manifest);m['components']['backdrops.json']={'exporter':'backdrop-dump/7','schema_version':7}
            different=dict(files,**{'backdrops.json':bundle.json_bytes(old)})
            for item in m['files']:
                if item['file']=='backdrops.json':item.update(bytes=len(different['backdrops.json']),sha256=hashlib.sha256(different['backdrops.json']).hexdigest())
            different['manifest.json']=bundle.json_bytes(m)
            with self.assertRaisesRegex(project.InputError,'existing research bundle differs'):bundle.save_bundle(m,different,repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},files)

    def test_late_invalid_placement_before_any_output_or_reporting(self):
        raw=self.make([[],[(2,definitions([refresh_header(1)])),
            (3,placement_block([0],coordinates())),(3,placement_block([1],coordinates())) ]])
        for module,save in ((backdrop,'save_backdrops'),(bundle,'save_bundle')):
            stderr=io.StringIO()
            with patch.object(module.sys,'argv',['export','unused','--klikback-src',os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path,'read_bytes',return_value=raw),patch.object(module,save) as write, \
                    patch.object(project,'report_fault') as report,redirect_stderr(stderr):
                self.assertEqual(module.main(),2);self.assertIn('placement pointer is unaligned or out of bounds',stderr.getvalue())
                write.assert_not_called();report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_source_spans_all_ordinary_candidates(self):
        path=Path(os.environ['FF_TEST_PROJECT']);raw=path.read_bytes();game=self.reader.read(raw)
        doc=backdrop.backdrop_document(self.reader,raw);banks={}
        for sid,s in enumerate(game.segments):
            if s.ident==10:
                for slot,at,size in self.reader.walk_bank(s.data):banks[sid,slot]=(s.offset+6+at,at,size)
        count=0
        for level,frame in zip(game.levels(),doc['frames']):
            blocks=self.reader.level_blocks(level.data)[1]
            for b in frame['placement_refresh_probes']:
                p=blocks[b['block_id']];base=level.offset+6+p.offset+6+2+4*int.from_bytes(p.data[:2],'little')
                for r in b['records']:
                    stored=raw[base+r['id']*32:base+(r['id']+1)*32]
                    for c in r['candidates']:
                        ann=c['conditional_ordinary_rectangle_inputs']
                        if c['type']!=1 or c['deleted']:self.assertIsNone(ann);continue
                        d=blocks[c['definition_block_id']];at=level.offset+6+d.offset+6+c['object_list_offset']
                        image=int.from_bytes(raw[at+54:at+56],'little')
                        self.assertEqual(ann['image_word']['raw_u16'],image)
                        records=[]
                        for v in ann['dimension_candidates']:
                            absolute,offset,size=banks[v['segment_id'],image]
                            self.assertEqual(v['bank_offset'],offset);self.assertEqual(v['image_id'],image)
                            records.append(raw[absolute:absolute+size])
                        assert_inputs(self,ann,stored,records);count+=1
        self.assertEqual(count,5021)
        self.assertEqual(path.read_bytes(),raw);self.assertEqual(backdrop.backdrop_document(self.reader,raw),doc)


if __name__=='__main__':unittest.main()
