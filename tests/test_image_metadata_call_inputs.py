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
from test_backdrop_dump import header
from test_backdrop_placement_probes import definitions, synthetic
from test_backdrop_refresh import refresh_header
from test_frame_layout import placement_block
from test_quick_rectangle_inputs import coordinates


def assert_call(test, ann, raw, kind):
    image = int.from_bytes(raw[8:10], 'little')
    fill = int.from_bytes(raw[24:26], 'little') & 15
    if kind != 1 and (kind != 0 or fill != 1 or not image):
        test.assertIsNone(ann)
        return
    test.assertFalse(ann['runtime_resolution'])
    test.assertFalse(ann['metadata_lookup_performed'])
    test.assertFalse(ann['drawing_performed'])
    test.assertEqual(ann['callee_argument_interpretation'], 'unresolved')
    test.assertEqual(ann['image_word'], {'record_offset':8, 'raw_u16':image})
    test.assertEqual(ann['arguments_in_stack_order'], ['runtime_context','image_argument','output_buffer'])
    test.assertEqual(ann['runtime_context_input'], {'runtime_dword_address':'0x41d4e4', 'raw_u32':None})
    test.assertEqual(ann['output_buffer_input'], {'storage':'caller_stack', 'runtime_address':None})
    test.assertEqual(ann['callee_thunk_address'], '0x414186')
    arg = ann['image_argument']
    if kind == 0:
        test.assertEqual(ann['path'], 'quick_mosaic')
        test.assertEqual(ann['call_instruction_address'], '0x405528')
        test.assertEqual(arg, {'low_u16':image, 'high_u16':0, 'raw_u32':image, 'rule':'zero_extended_image_word'})
    else:
        x = struct.unpack_from('<h', raw, 2)[0]
        test.assertEqual(ann['path'], 'ordinary')
        test.assertEqual(ann['call_instruction_address'], '0x4058a9')
        test.assertEqual(arg['low_u16'], image)
        test.assertIsNone(arg['high_u16']); test.assertIsNone(arg['raw_u32'])
        test.assertEqual(arg['rule'], '((translated_origin_x & 0xFFFF) << 16) | image_word')
        test.assertEqual(arg['zero_translation_argument_raw_u32'], (int.from_bytes(raw[2:4],'little') << 16) | image)
        test.assertEqual(arg['origin_x_input'], {'record_offset':2, 'raw_u16':int.from_bytes(raw[2:4],'little'),
            'signed_i16':x, 'runtime_translation_word_address':'0x41d662',
            'runtime_translation_signed_i16':None, 'rule':'signed_record_x - signed_runtime_translation_x'})


class ImageMetadataCallTests(unittest.TestCase):
    def test_quick_dispatch_all_fill_high_bytes_and_handles(self):
        for high in range(256):
            for low in (0,1,2,16,17,18):
                for image in (0,1,32768,65535):
                    with self.subTest(high=high,low=low,image=image):
                        raw=bytearray(coordinates());struct.pack_into('<HH',raw,8,image,65535)
                        struct.pack_into('<H',raw,24,(high<<8)|low)
                        assert_call(self,backdrop.image_metadata_call_inputs(raw,0),raw,0)

    def test_ordinary_zero_translation_probe_and_no_image_sentinel(self):
        for x in (0,1,32767,32768,32769,65534,65535):
            for image in (0,1,32767,32768,65535):
                with self.subTest(x=x,image=image):
                    raw=bytearray(coordinates(x=x));struct.pack_into('<HH',raw,8,image,0xA5A5)
                    assert_call(self,backdrop.image_metadata_call_inputs(raw,1),raw,1)

    def test_complete_record_opaque_neighbors_and_unsupported_kinds(self):
        raw=bytearray(coordinates());struct.pack_into('<H',raw,24,1)
        for kind in (0,1):
            original=bytes(raw);expected=backdrop.image_metadata_call_inputs(raw,kind)
            for at in (0,1,4,5,6,7,10,11,12,13,16,20,26,27,28,29,30,31):raw[at]^=255
            self.assertNotEqual(raw,original)
            self.assertEqual(backdrop.image_metadata_call_inputs(raw,kind),expected)
            raw[:]=original
        for kind in (2,255,-1):self.assertIsNone(backdrop.image_metadata_call_inputs(raw,kind))
        for bad in (b'',bytes(raw[:-1]),bytes(raw)+b'x'):
            with self.assertRaisesRegex(project.InputError,'complete placement record'):backdrop.image_metadata_call_inputs(bad,1)
        raw[24]=3
        with self.assertRaisesRegex(project.InputError,'dispatch nibble'):backdrop.image_metadata_call_inputs(raw,0)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'),'set FF_KLIKBACK_SRC for parser tests')
class ImageMetadataCallContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_candidates_global_ambiguity_other_types_and_missing(self):
        local=bytearray(refresh_header(1,image=2));local[38]=0
        raw=synthetic(self.reader,[[(2,definitions([refresh_header(1)]))],
            [(2,definitions([refresh_header(1)])),(2,definitions([bytes(local)])),
             (2,definitions([refresh_header(0,fill=1)])),(2,definitions([refresh_header(0,fill=2)])),
             (2,definitions([header(255),header(2)])),
             (3,placement_block([0,32,64],coordinates()+coordinates(1)+coordinates(65535))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        records=doc['frames'][1]['placement_refresh_probes'][0]['records']
        candidates=records[0]['candidates']
        self.assertEqual([c['global'] for c in candidates],[True,False,True,True,True])
        self.assertEqual([c['conditional_image_metadata_call_inputs']['image_word']['raw_u16'] for c in candidates[:3]],[5,2,5])
        for r in records:
            for c in r['candidates']:
                assert_call(self,c['conditional_image_metadata_call_inputs'],bytes.fromhex(c['conditional_record_hex'] or r['raw_hex']), c['type'] if not c['deleted'] else 255)
        self.assertEqual(records[2]['candidates'],[])
        self.assertTrue(doc['coverage']['conditional_image_metadata_call_inputs'])
        for key in ('runtime_rendering','global_reference_resolution','arena_geometry','spawns','behaviour'):self.assertFalse(doc['coverage'][key])

    def test_aliases_reversed_gaps_empty_absent_and_repeated_placements(self):
        raw=synthetic(self.reader,[[],[(2,definitions([refresh_header(1)])),
            (3,placement_block([32,0xffffffff,0,32],coordinates(x=65535)+coordinates(x=32768))),
            (3,placement_block([],b'')),(3,placement_block([0],coordinates(x=1))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        self.assertEqual(doc['frames'][0]['placement_refresh_probes'],[])
        blocks=doc['frames'][1]['placement_refresh_probes']
        self.assertEqual([s['record_id'] for s in blocks[0]['slots']],[1,None,0,1])
        self.assertEqual(blocks[1]['records'],[])
        for b in blocks:
            for r in b['records']:
                for c in r['candidates']:assert_call(self,c['conditional_image_metadata_call_inputs'],bytes.fromhex(c['conditional_record_hex']),1)

    def test_bundle_standalone_repeats_and_previous_schema_refusal(self):
        raw=synthetic(self.reader,[[],[(2,definitions([refresh_header(1)])),(3,placement_block([0],coordinates()))]])
        doc=backdrop.backdrop_document(self.reader,raw);m,files=bundle.research_bundle(self.reader,raw)
        self.assertEqual(json.loads(files['backdrops.json']),doc)
        self.assertEqual(m['components']['backdrops.json'], {'exporter':'backdrop-dump/9','schema_version':9})
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo=Path(scratch);target=bundle.save_bundle(m,files,repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader,raw),repo),target)
            for _ in range(2):self.assertEqual(backdrop.save_backdrops(doc,repo).read_bytes(),files['backdrops.json'])
            old=copy.deepcopy(doc)
            for f in old['frames']:
                for b in f['placement_refresh_probes']:
                    for r in b['records']:
                        for c in r['candidates']:c.pop('conditional_image_metadata_call_inputs')
            old['coverage'].pop('conditional_image_metadata_call_inputs');old['schema_version']=8;old['exporter']='backdrop-dump/8'
            manifest=copy.deepcopy(m);manifest['components']['backdrops.json']={'exporter':'backdrop-dump/8','schema_version':8}
            different=dict(files,**{'backdrops.json':bundle.json_bytes(old)})
            for item in manifest['files']:
                if item['file']=='backdrops.json':item.update(bytes=len(different['backdrops.json']),sha256=hashlib.sha256(different['backdrops.json']).hexdigest())
            different['manifest.json']=bundle.json_bytes(manifest)
            with self.assertRaisesRegex(project.InputError,'existing research bundle differs'):bundle.save_bundle(manifest,different,repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},files)

    def test_late_invalid_before_output_or_fault_reporting(self):
        raw=synthetic(self.reader,[[],[(2,definitions([refresh_header(1)])),
            (3,placement_block([0],coordinates())),(3,placement_block([1],coordinates())) ]])
        for module,save in ((backdrop,'save_backdrops'),(bundle,'save_bundle')):
            with patch.object(module.sys,'argv',['export','unused','--klikback-src',os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path,'read_bytes',return_value=raw),patch.object(module,save) as write, \
                    patch.object(project,'report_fault') as report,redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(),2);write.assert_not_called();report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'),'set FF_TEST_PROJECT for local original')
    def test_original_independent_absolute_source_all_placement_candidates(self):
        path=Path(os.environ['FF_TEST_PROJECT']);raw=path.read_bytes();game=self.reader.read(raw)
        doc=backdrop.backdrop_document(self.reader,raw);counts={'ordinary':0,'quick_mosaic':0,'no_call':0}
        for level,frame in zip(game.levels(),doc['frames']):
            blocks=self.reader.level_blocks(level.data)[1]
            for b in frame['placement_refresh_probes']:
                p=blocks[b['block_id']];base=level.offset+6+p.offset+6+2+4*int.from_bytes(p.data[:2],'little')
                for r in b['records']:
                    stored=raw[base+r['id']*32:base+(r['id']+1)*32]
                    for c in r['candidates']:
                        ann=c['conditional_image_metadata_call_inputs']
                        if c['type'] not in (0,1) or c['deleted']:
                            self.assertIsNone(ann);continue
                        d=blocks[c['definition_block_id']];at=level.offset+6+d.offset+6+c['object_list_offset']
                        head=raw[at:at+68];preview=bytearray(stored);preview[8:10]=head[54:56]
                        if head[42]==0:preview[24:26]=head[32:34]
                        assert_call(self,ann,preview,head[42])
                        counts['no_call' if ann is None else ann['path']]+=1
        self.assertEqual(counts,{'ordinary':5021,'quick_mosaic':45,'no_call':24})
        self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(backdrop.backdrop_document(self.reader,raw),doc)


if __name__=='__main__':unittest.main()
