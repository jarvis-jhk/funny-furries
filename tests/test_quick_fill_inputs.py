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
from test_backdrop_placement_probes import definitions, record, synthetic
from test_backdrop_refresh import refresh_header
from test_backdrop_dump import header
from test_frame_layout import placement_block


def fill_header(fill=2, high=1, image=65535, colors=(0xF1345678, 0x9ABCDEF0)):
    raw = bytearray(refresh_header(fill=fill))
    struct.pack_into('<IIH', raw, 24, *colors, fill | high << 8)
    struct.pack_into('<H', raw, 54, image)
    return bytes(raw)


def assert_inputs(test, out, head):
    word = int.from_bytes(head[32:34], 'little')
    image = int.from_bytes(head[54:56], 'little')
    colors = [int.from_bytes(head[at:at+4], 'little') for at in (24,28)]
    kind = word & 15
    branch = 'gradient' if kind == 2 else 'mosaic_metadata_required' if kind == 1 and image != 0 else 'solid'
    test.assertEqual(out['fill_word'], {'record_offset':24, 'raw_u16':word,'dispatch_nibble':kind})
    test.assertEqual(out['image_word'], {'record_offset':8,'raw_u16':image})
    test.assertEqual(out['colors'], [{'record_offset':at,'raw_u32':value} for at,value in zip((16,20),colors)])
    test.assertEqual(out['branch'], branch)
    test.assertEqual(out['mosaic_zero_image_solid_fallback'], kind == 1 and image == 0)
    test.assertEqual(out['solid_color_raw_u32'], colors[0] if branch == 'solid' else None)
    if kind == 2:
        test.assertEqual(out['gradient_arguments'], {
            'swap_colors':bool(head[33] & 1), 'swap_mask':256,
            'first_color_raw_u32': colors[head[33] & 1],
            'second_color_raw_u32':colors[1 - (head[33] & 1)],
            'flags_mask':240,'flags_raw_u16':head[32] & 240,
            'flags_high_u16_input':None,
            'flags_argument_rule':'(incoming_edx & 0xFFFF0000) | (refreshed_fill_word & 0x00F0)' })
    else:
        test.assertIsNone(out['gradient_arguments'])
    test.assertEqual(out['clipping_inputs'], {n:{'signed_i32':None} for n in ('origin_x','origin_y','right_clip','bottom_clip')})
    test.assertEqual(out['inclusive_endpoint_rule'], 'signed_min(origin + signed_refreshed_dimension - 1, clip)')
    test.assertEqual(out['arithmetic'], 'x86_32bit_wrap_before_signed_min')
    test.assertFalse(out['runtime_resolution']); test.assertFalse(out['drawing_performed'])


class QuickFillTests(unittest.TestCase):
    def test_full_word_gradient_swap_is_independent_of_orientation(self):
        for high in range(256):
            for fill in (2,18):
                with self.subTest(high=high, fill=fill):
                    head = fill_header(fill,high)
                    raw = bytearray(record(0)); raw[16:30] = head[24:38]; raw[8:10]=head[54:56]
                    ann = backdrop.quick_fill_inputs(raw)
                    assert_inputs(self,ann,head)
                    self.assertEqual(ann['gradient_arguments']['swap_colors'], bool(high % 2))

    def test_solid_mosaic_zero_fallback_and_nonzero_handles(self):
        for fill in (0,1,16,17):
            for image in (0,1,32768,65535):
                head = fill_header(fill,255,image)
                raw = bytearray(record(0));raw[16:30]=head[24:38];raw[8:10]=head[54:56]
                with self.subTest(fill=fill,image=image):
                    assert_inputs(self,backdrop.quick_fill_inputs(raw),head)

    def test_bad_lengths_dispatch_and_opaque_neighbours(self):
        raw = bytearray(record(0));raw[24:26]=b'\x12\xab'
        ann=backdrop.quick_fill_inputs(raw);before=bytes(raw)
        for at in (0,1,2,3,4,5,6,7,10,11,12,13,14,15,26,27,28,29,30,31):raw[at]^=255
        self.assertEqual(backdrop.quick_fill_inputs(raw),ann)
        self.assertNotEqual(bytes(raw),before)
        for data in (b'',before[:-1],before+b'x'):
            with self.assertRaisesRegex(project.InputError,'complete placement record'):backdrop.quick_fill_inputs(data)
        for kind in range(3,16):
            raw[24]=kind
            with self.subTest(kind=kind),self.assertRaisesRegex(project.InputError,'dispatch nibble'):backdrop.quick_fill_inputs(raw)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class QuickFillContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_ambiguous_local_global_quick_headers_and_other_types(self):
        a=fill_header(2,1);b=bytearray(fill_header(18,2));b[38]=0;b=bytes(b)
        raw=synthetic(self.reader,[[],[(2,definitions([a])),(2,definitions([b])),
            (2,definitions([refresh_header(1)])),(2,definitions([header(255),header(2)])),
            (3,placement_block([0,32,64],record(0)+record(1)+record(65535))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        out=doc['frames'][1]['placement_refresh_probes'][0]['records']
        self.assertEqual(out[0]['status'],'multiple_local_candidates')
        self.assertEqual([c['global'] for c in out[0]['candidates']],[True,False,True,True])
        for c,h in zip(out[0]['candidates'][:2],(a,b)):assert_inputs(self,c['conditional_quick_fill_inputs'],h)
        for c in out[0]['candidates'][2:]+out[1]['candidates']:self.assertIsNone(c['conditional_quick_fill_inputs'])
        self.assertEqual(out[2]['candidates'],[])
        self.assertTrue(doc['coverage']['conditional_quick_fill_inputs'])
        for name in ('runtime_rendering','global_reference_resolution','arena_geometry','spawns','behaviour'):self.assertFalse(doc['coverage'][name])

    def test_aliases_reversed_pointers_absent_empty_and_repeated_blocks(self):
        head=fill_header()
        raw=synthetic(self.reader,[[],[(2,definitions([head])),
            (3,placement_block([32,0xFFFFFFFF,0,32],record(0)+record(0,11))),
            (3,placement_block([],b'')),(3,placement_block([0],record(0,22))) ]])
        doc=backdrop.backdrop_document(self.reader,raw)
        self.assertEqual(doc['frames'][0]['placement_refresh_probes'],[])
        blocks=doc['frames'][1]['placement_refresh_probes']
        self.assertEqual([s['record_id'] for s in blocks[0]['slots']],[1,None,0,1])
        self.assertEqual(blocks[1]['records'],[])
        for b in blocks:
            for r in b['records']:assert_inputs(self,r['candidates'][0]['conditional_quick_fill_inputs'],head)

    def test_standalone_bundle_repeat_immutable_refusal(self):
        raw=synthetic(self.reader,[[],[(2,definitions([fill_header()])),(3,placement_block([0],record(0))) ]])
        doc=backdrop.backdrop_document(self.reader,raw);manifest,files=bundle.research_bundle(self.reader,raw)
        self.assertEqual(json.loads(files['backdrops.json']),doc)
        self.assertEqual(manifest['components']['backdrops.json'],{'exporter':'backdrop-dump/8','schema_version':8})
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo=Path(scratch);target=bundle.save_bundle(manifest,files,repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader,raw),repo),target)
            self.assertEqual(backdrop.save_backdrops(doc,repo).read_bytes(),files['backdrops.json'])
            old=copy.deepcopy(doc)
            for f in old['frames']:
                for b in f['placement_refresh_probes']:
                    for r in b['records']:
                        for c in r['candidates']:c.pop('conditional_quick_fill_inputs')
            old['coverage'].pop('conditional_quick_fill_inputs');old['schema_version']=6;old['exporter']='backdrop-dump/6'
            different=dict(files,**{'backdrops.json':bundle.json_bytes(old)})
            old_manifest=copy.deepcopy(manifest);old_manifest['components']['backdrops.json']={'exporter':'backdrop-dump/6','schema_version':6}
            for item in old_manifest['files']:
                if item['file']=='backdrops.json':item.update(bytes=len(different['backdrops.json']),sha256=hashlib.sha256(different['backdrops.json']).hexdigest())
            different['manifest.json']=bundle.json_bytes(old_manifest)
            with self.assertRaisesRegex(project.InputError,'existing research bundle differs'):bundle.save_bundle(old_manifest,different,repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},files)

    def test_late_bad_header_before_output_or_reporting(self):
        raw=synthetic(self.reader,[[],[(2,definitions([fill_header(),refresh_header(fill=3)])),(3,placement_block([0,32],record(0)+record(1))) ]])
        for module,save in ((backdrop,'save_backdrops'),(bundle,'save_bundle')):
            stderr=io.StringIO()
            with self.subTest(module=module.VERSION),patch.object(module.sys,'argv',['export','unused','--klikback-src',os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path,'read_bytes',return_value=raw),patch.object(module,save) as write,patch.object(project,'report_fault') as report,redirect_stderr(stderr):
                self.assertEqual(module.main(),2);self.assertIn('unsupported quick backdrop fill flags',stderr.getvalue())
                write.assert_not_called();report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_absolute_source_spans_all_quick_candidates(self):
        path=Path(os.environ['FF_TEST_PROJECT']);raw=path.read_bytes();doc=backdrop.backdrop_document(self.reader,raw);game=self.reader.read(raw)
        count=0;branches={};highs=set()
        for level,frame in zip(game.levels(),doc['frames']):
            blocks=self.reader.level_blocks(level.data)[1]
            for b in frame['placement_refresh_probes']:
                for r in b['records']:
                    for c in r['candidates']:
                        if c['type']!=0 or c['deleted']:
                            self.assertIsNone(c['conditional_quick_fill_inputs']);continue
                        d=blocks[c['definition_block_id']];at=level.offset+6+d.offset+6+c['object_list_offset'];head=raw[at:at+68]
                        self.assertEqual(int.from_bytes(head[42:44],'little') & 255,0)
                        ann=c['conditional_quick_fill_inputs'];assert_inputs(self,ann,head)
                        count+=1;branches[ann['branch']]=branches.get(ann['branch'],0)+1;highs.add(head[33])
        self.assertEqual(count,69);self.assertEqual(branches,{'gradient':24,'mosaic_metadata_required':45})
        self.assertEqual(highs,{0})
        self.assertEqual(path.read_bytes(),raw);self.assertEqual(backdrop.backdrop_document(self.reader,raw),doc)


if __name__=='__main__':unittest.main()
