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
from test_backdrop_refresh import refresh_header
from test_frame_layout import placement_block


def block(kind, data):
    return struct.pack('<HI', kind, len(data)) + data


def definitions(heads):
    return struct.pack('<HH', len(heads), 0) + b''.join(h + (block(0x8000, b'opaque') if h[42] != 255 and not h[38] & 128 else b'') for h in heads)


def record(slot, seed=0):
    raw = bytearray((i * 7 + seed) & 255 for i in range(32))
    struct.pack_into('<H', raw, 0, slot)
    return bytes(raw)


def synthetic(reader, frame_blocks):
    base = project_bytes()
    # Reuse only valid synthetic asset/global banks; frame layout is independent.
    segments = [(s.ident, s.data) for s in reader.read(base).segments if s.ident != 8]
    segments += [(8, bytes(184) + b''.join(block(k | (0x8000 if i == len(blocks)-1 else 0), v) for i, (k, v) in enumerate(blocks or [(0x8000, b'')]))) for blocks in frame_blocks]
    head = bytearray(base[:366]); struct.pack_into('<H', head, 348, len(frame_blocks))
    cursor = len(head); addresses = []
    for kind, data in segments:
        if kind == 8:
            addresses.append(cursor + 6)
        cursor += 6 + len(data)
    struct.pack_into('<2I', head, 358, *addresses)
    return bytes(head) + b''.join(block(k | (0x8000 if i == len(segments)-1 else 0), data) for i, (k, data) in enumerate(segments))


def expected(head, raw):
    # Independent byte spans, without production annotations/write descriptors.
    result = bytearray(raw)
    result[12:16] = head[50:54]
    result[6:8] = (int.from_bytes(head[42:44], 'little') & 4095).to_bytes(2, 'little')
    if head[42] == 0:
        result[16:30] = head[24:38]
    result[8:10] = head[54:56]
    return result.hex()


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class PlacementRefreshProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def document(self, frames):
        return backdrop.backdrop_document(self.reader, synthetic(self.reader, frames))

    def test_quick_ordinary_conditional_bytes_and_untouched_coordinates(self):
        heads = [refresh_header(0, 255, 2), refresh_header(1, 171)]
        records = [record(0), record(1)]
        doc = self.document([[], [(2, definitions(heads)), (3, placement_block([0,32], b''.join(records))) ]])
        outputs = doc['frames'][1]['placement_refresh_probes'][0]['records']
        for out, head, raw in zip(outputs, heads, records):
            c = out['candidates'][0]
            self.assertEqual(c['conditional_record_hex'], expected(head, raw))
            self.assertEqual(c['header_sha256'], hashlib.sha256(head).hexdigest())
            self.assertEqual(out['raw_hex'], raw.hex())
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(bytes.fromhex(c['conditional_record_hex'])[:6], raw[:6])
            self.assertEqual(c['status'], 'conditional_backdrop_refresh')
        # Stored creation type intentionally differs; it must not filter probes.
        self.assertNotEqual(records[0][6], 0)
        self.assertTrue(doc['coverage']['local_placement_refresh_probes'])
        self.assertFalse(doc['coverage']['arena_geometry'])

    def test_frame_scope_no_global_fallback_unsigned_words_and_non_backdrops(self):
        frames = [[(2, definitions([refresh_header(1)])), (3, placement_block([0], record(0)))],
                  [(2, definitions([header(2), header(255)])),
                   (3, placement_block([0,32,64,96,128], b''.join(record(n) for n in (0,1,2,0x4000,65535))))]]
        doc = self.document(frames)
        out = doc['frames'][1]['placement_refresh_probes'][0]['records']
        self.assertEqual(out[0]['candidates'][0]['status'], 'non_backdrop_definition')
        self.assertEqual(out[1]['candidates'][0]['status'], 'deleted_definition')
        for item in out[:2]:
            self.assertIsNone(item['candidates'][0]['conditional_record_hex'])
        for item in out[2:]:
            self.assertEqual(item['status'], 'missing_local_slot')
            self.assertEqual(item['candidates'], [])
        self.assertEqual([v['object_word_raw_u16'] for v in out], [0,1,2,0x4000,65535])

    def test_ambiguous_lists_keep_local_global_flags_and_all_type_candidates(self):
        a = refresh_header(0)
        b = bytearray(refresh_header(1, 250)); b[38] = 0; b = bytes(b)
        doc = self.document([[], [(0, b'opaque'), (2, definitions([a])),
                                 (2, definitions([b])), (2, definitions([header(255)])),
                                 (3, placement_block([0], record(0))) ]])
        out = doc['frames'][1]['placement_refresh_probes'][0]['records'][0]
        self.assertEqual(out['status'], 'multiple_local_candidates')
        self.assertEqual([c['definition_block_id'] for c in out['candidates']], [1,2,3])
        self.assertEqual([c['type'] for c in out['candidates']], [0,1,255])
        self.assertEqual([c['global'] for c in out['candidates']], [True,False,True])
        self.assertEqual([c['conditional_record_hex'] for c in out['candidates']],
                         [expected(a, record(0)), expected(b, record(0)), None])

    def test_gaps_aliases_reversed_pointers_and_absent_empty_repeated_blocks(self):
        doc = self.document([[], [(2, definitions([refresh_header()])),
                    (3, placement_block([32,0xFFFFFFFF,0,32], record(0)+record(65535))),
                    (3, placement_block([], b'')), (3, placement_block([0], record(0,2))) ]])
        self.assertEqual(doc['frames'][0]['placement_refresh_probes'], [])
        probes = doc['frames'][1]['placement_refresh_probes']
        self.assertEqual([p['block_id'] for p in probes], [1,2,3])
        self.assertEqual([s['record_id'] for s in probes[0]['slots']], [1,None,0,1])
        self.assertEqual([r['offset'] for r in probes[0]['records']], [18,50])
        self.assertEqual(probes[1]['records'], [])
        self.assertEqual(probes[1]['slots'], [])
        self.assertEqual(len(probes[0]['records']), 2)
        self.assertNotEqual(probes[0]['records'][0]['raw_hex'], probes[2]['records'][0]['raw_hex'])

    def test_high_type_bits_fill_word_and_unsigned_image_preserved(self):
        for kind in (0,1):
            for high in (0,15,16,171,255):
                h = refresh_header(kind, high, 0, 65535 if kind==0 else 5)
                doc = self.document([[], [(2, definitions([h])), (3, placement_block([0], record(0))) ]])
                out = doc['frames'][1]['placement_refresh_probes'][0]['records'][0]['candidates'][0]
                self.assertEqual(out['conditional_record_hex'], expected(h, record(0)))

    def test_bundle_standalone_repeat_and_immutable_previous_bundle(self):
        raw = synthetic(self.reader, [[], [(2, definitions([refresh_header()])), (3, placement_block([0], record(0))) ]])
        doc = backdrop.backdrop_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(json.loads(files['backdrops.json']), doc)
        self.assertEqual(manifest['components']['backdrops.json'], {'exporter':'backdrop-dump/7','schema_version':7})
        (project.REPO/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO/'build') as scratch:
            repo = Path(scratch)
            target = bundle.save_bundle(manifest, files, repo)
            self.assertEqual(bundle.save_bundle(*bundle.research_bundle(self.reader, raw), repo), target)
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), files['backdrops.json'])
            self.assertEqual(backdrop.save_backdrops(doc, repo).read_bytes(), files['backdrops.json'])
            mutated = copy.deepcopy(doc)
            mutated['frames'][1]['placement_refresh_probes'][0]['records'][0]['candidates'][0]['conditional_record_hex'] = '00'*32
            other = dict(files, **{'backdrops.json':bundle.json_bytes(mutated)})
            m = copy.deepcopy(manifest)
            for f in m['files']:
                if f['file']=='backdrops.json':
                    f.update(bytes=len(other['backdrops.json']),sha256=hashlib.sha256(other['backdrops.json']).hexdigest())
            other['manifest.json'] = bundle.json_bytes(m)
            with self.assertRaisesRegex(project.InputError, 'existing research bundle differs'):
                bundle.save_bundle(m, other, repo)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()}, files)

    def test_late_malformed_placement_before_any_output_or_fault_report(self):
        raw = synthetic(self.reader, [[], [(2, definitions([refresh_header()])),
                     (3, placement_block([0], record(0))), (3, placement_block([1], record(0))) ]])
        for module, save in ((backdrop, 'save_backdrops'), (bundle, 'save_bundle')):
            stderr = io.StringIO()
            with self.subTest(module=module.VERSION), patch.object(module.sys, 'argv', ['export','unused','--klikback-src',os.environ['FF_KLIKBACK_SRC']]), \
                    patch.object(Path,'read_bytes',return_value=raw), patch.object(module,save) as write, \
                    patch.object(project,'report_fault') as report, redirect_stderr(stderr):
                self.assertEqual(module.main(), 2)
                self.assertIn('placement pointer is unaligned or out of bounds', stderr.getvalue())
                write.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_slot_header_record_spans(self):
        path=Path(os.environ['FF_TEST_PROJECT']); raw=path.read_bytes()
        doc=backdrop.backdrop_document(self.reader,raw); game=self.reader.read(raw)
        counts={'records':0,'backdrops':0,'quick':0,'ordinary':0}
        for level, frame in zip(game.levels(),doc['frames']):
            blocks=self.reader.level_blocks(level.data)[1]; local={}
            for block_id,b in enumerate(blocks):
                if b.ident==2:
                    for o in self.reader.object_definitions(b.data):
                        local.setdefault(o.index,[]).append((block_id,o,b))
            for out in frame['placement_refresh_probes']:
                b=blocks[out['block_id']]; n=int.from_bytes(b.data[:2],'little'); start=2+4*n
                absolute=level.offset+6+b.offset+6
                self.assertEqual(out['placement_sha256'],hashlib.sha256(raw[absolute:absolute+len(b.data)]).hexdigest())
                for r in out['records']:
                    source=raw[absolute+start+r['id']*32:absolute+start+(r['id']+1)*32]
                    self.assertEqual(r['raw_hex'],source.hex()); counts['records']+=1
                    matches=local[int.from_bytes(source[:2],'little')]
                    self.assertEqual(len(r['candidates']),len(matches))
                    for c,(bid,o,definition) in zip(r['candidates'],matches):
                        self.assertEqual((c['definition_block_id'],c['id'],c['object_list_offset']),(bid,o.index,o.base))
                        if o.object_type in (0,1):
                            at=level.offset+6+definition.offset+6+o.base
                            head=raw[at:at+68]
                            self.assertEqual(c['conditional_record_hex'],expected(head,source))
                            self.assertEqual(c['header_sha256'],hashlib.sha256(head).hexdigest())
                            counts['backdrops']+=1; counts['quick' if o.object_type==0 else 'ordinary']+=1
                        else:
                            self.assertIsNone(c['conditional_record_hex'])
                    self.assertFalse(r['runtime_resolution'])
        self.assertEqual(counts['records'],7968)
        self.assertGreater(counts['quick'],0); self.assertGreater(counts['ordinary'],0)
        self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(backdrop.backdrop_document(self.reader,raw),doc)


if __name__=='__main__':
    unittest.main()
