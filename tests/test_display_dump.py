import collections
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import display_dump as display
from tools import project_index as project


def image_section(images=(2, 5, 5), kind=1):
    return struct.pack('<4H', 8 + 2 * len(images), kind, 0xABCD, len(images)) + struct.pack(
        f'<{len(images)}H', *images)


def opaque_section(kind=3):
    return struct.pack('<HH', 10, kind) + b'\xff\xff\x12\x34\x56\x78'


def display_data(kind=7, sections=None):
    attributes = struct.pack('<H', 6) + b'\x01\xff\x03\x80' if kind == 7 else b''
    sections = sections if sections is not None else [image_section(), opaque_section()]
    return bytes(range(42)) + display.SIGNATURES[kind] + attributes + b''.join(sections)


def project_bytes(data=None, repeated=False):
    def block(kind, payload):
        return struct.pack('<HI', kind, len(payload)) + payload
    def obj(kind, flags=0, payload=None):
        head = bytearray(68)
        head[38], head[42] = flags, kind
        return bytes(head) + (block(0x8000, payload) if payload is not None else b'')
    globals_ = block(6, struct.pack('<HH', 1, 0) + obj(5, 128, display_data(5)))
    objects = struct.pack('<HH', 5, 0) + obj(7, payload=data if data is not None else display_data())
    objects += obj(255) + obj(6, 128) + obj(2, 128) + obj(6, payload=display_data(6, [image_section((), 4)]))
    frames = [bytes(184) + block(0x8000, b'palette'),
              bytes(184) + block(2, struct.pack('<HH', 0, 0)) + block(0x8002, objects)]
    head = bytearray(366)
    head[:4] = b'GAME'
    struct.pack_into('<H', head, 4, 0x0207)
    struct.pack_into('<H', head, 348, 2)
    struct.pack_into('<II', head, 358, len(head) + len(globals_) + 6,
                     len(head) + len(globals_) + len(frames[0]) + 12)
    bank = bytearray(4 + 6 * 8)
    struct.pack_into('<I', bank, 0, 6)
    for slot in (2, 5):
        struct.pack_into('<II', bank, 4 + slot * 8, len(bank), 1)
        bank += b'x'
    banks = block(10 if repeated else 0x800A, bank)
    if repeated:
        banks += block(10, struct.pack('<I', 0)) + block(0x800A, bank)
    return bytes(head) + globals_ + block(8, frames[0]) + block(8, frames[1]) + banks


class DisplayTests(unittest.TestCase):
    def test_all_signatures_ordered_handles_opaque_sections_and_reconstruction(self):
        for kind in (5, 6, 7):
            with self.subTest(kind=kind):
                raw = display_data(kind, [image_section(), opaque_section(65535), image_section((5, 2), 4)])
                out = display.decode_display(raw, kind)
                self.assertEqual(out['raw_hex'], raw.hex())
                self.assertEqual(out['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual([s['image_ids'] for s in out['sections']], [[2, 5, 5], None, [5, 2]])
                self.assertEqual([s['type_raw_u16'] for s in out['sections']], [1, 65535, 4])
                self.assertEqual([s['id'] for s in out['sections']], [0, 1, 2])
                rebuilt = bytes.fromhex(out['prefix_hex'])
                attributes = out['counter_attributes']
                if kind == 7:
                    self.assertEqual(attributes, {'offset': 46, 'bytes': 6, 'raw_hex': '060001ff0380'})
                    rebuilt += bytes.fromhex(attributes['raw_hex'])
                else:
                    self.assertIsNone(attributes)
                for section in out['sections']:
                    self.assertEqual(section['offset'], len(rebuilt))
                    rebuilt += bytes.fromhex(section['raw_hex'])
                self.assertEqual(rebuilt, raw)

    def test_empty_images_opaque_zero_mode_and_absent_sections(self):
        out = display.decode_display(display_data(7, [image_section(()), opaque_section(0)]), 7)
        self.assertEqual(out['sections'][0]['image_ids'], [])
        self.assertIsNone(out['sections'][1]['image_ids'])
        self.assertEqual(out['sections'][1]['raw_hex'], opaque_section(0).hex())
        for kind in (5, 6, 7):
            with self.subTest(kind=kind), self.assertRaises(project.InputError):
                display.decode_display(display_data(kind, []), kind)

    def test_signature_attribute_section_extents_counts_and_trailing_bytes(self):
        raw = display_data()
        bad = [b'', raw[:47], raw[:42] + b'NOPE' + raw[46:], raw + b'x', raw[:-1]]
        for at, value in [(46, 0), (46, 1), (46, 65535), (46, len(raw) - 46),
                          (52, 0), (52, 3), (52, 7), (52, 65535), (58, 0), (58, 65535)]:
            changed = bytearray(raw)
            struct.pack_into('<H', changed, at, value)
            bad.append(changed)
        bad += [display_data(7, [struct.pack('<HH', 4, 1)]),
                display_data(7, [image_section() + b'zz'])]
        for changed in bad:
            with self.subTest(raw=changed), self.assertRaises(project.InputError):
                display.decode_display(changed, 7)
        with self.assertRaises(project.InputError):
            display.decode_display(raw, 2)
        with self.assertRaises(project.InputError):
            display.decode_display(raw, 5)

    def test_atomic_repeat_write_failure_and_symlink_refusal(self):
        doc = {'source': {'sha256': 'a' * 64}, 'value': 1}
        (project.REPO / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            repo = Path(scratch)
            target = display.save_displays(doc, repo)
            initial = target.read_bytes()
            self.assertEqual(json.loads(initial), doc)
            self.assertEqual(display.save_displays(doc, repo).read_bytes(), initial)
            with patch.object(project.os, 'replace', side_effect=OSError('synthetic')):
                with self.assertRaises(OSError):
                    display.save_displays({**doc, 'value': 2}, repo)
            self.assertEqual(target.read_bytes(), initial)
            self.assertEqual(list(target.parent.iterdir()), [target])
            victim = repo / 'victim'
            victim.write_bytes(b'keep')
            target.unlink()
            target.symlink_to(victim)
            with self.assertRaises(project.InputError):
                display.save_displays(doc, repo)
            self.assertEqual(victim.read_bytes(), b'keep')

    def test_fault_classification_and_safe_delivery_context(self):
        with patch.object(display.sys, 'argv', ['display', 'unused', '--klikback-src', 'unused']), \
                patch.object(project, 'report_fault') as report:
            with patch.object(project, 'load_reader', side_effect=project.InputError('bad')):
                self.assertEqual(display.main(), 2)
            report.assert_not_called()
            with patch.object(project, 'load_reader', side_effect=RuntimeError('private')):
                self.assertEqual(display.main(), 1)
            report.assert_called_once_with('RuntimeError', version=display.VERSION, title='Display exporter crashed')
            report.reset_mock()
            with patch.object(project, 'load_reader'), patch.object(Path, 'read_bytes', return_value=b''), \
                    patch.object(display, 'display_document', return_value={}), \
                    patch.object(display, 'save_displays', side_effect=OSError('private')):
                self.assertEqual(display.main(), 1)
            report.assert_called_once_with('OSError', version=display.VERSION, title='Display exporter crashed')


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_slots_reference_only_globals_repeated_banks_missing_and_empty_lists(self):
        doc = display.display_document(self.reader, project_bytes(repeated=True))
        self.assertEqual(doc['frames'][0]['object_lists'], [])
        lists = doc['frames'][1]['object_lists']
        self.assertEqual([v['block_id'] for v in lists], [0, 1])
        self.assertEqual(lists[0]['objects'], [])
        objects = lists[1]['objects']
        self.assertEqual([o['id'] for o in objects], list(range(5)))
        self.assertEqual([o['deleted'] for o in objects], [False, True, False, False, False])
        self.assertTrue(objects[2]['global'])
        self.assertEqual([objects[i]['display_data'] for i in (1, 2, 3)], [[], [], []])
        self.assertEqual([b['slots'] for b in doc['image_banks']], [[2, 5], [], [2, 5]])
        candidates = [doc['image_banks'][i]['segment_id'] for i in (0, 2)]
        sections = objects[0]['display_data'][0]['sections']
        self.assertEqual(sections[0]['image_ids'], [2, 5, 5])
        self.assertEqual(sections[0]['image_bank_candidates'], [candidates] * 3)
        self.assertIsNone(sections[1]['image_bank_candidates'])
        self.assertEqual(objects[4]['display_data'][0]['sections'][0]['image_ids'], [])
        self.assertEqual(objects[4]['display_data'][0]['sections'][0]['image_bank_candidates'], [])
        self.assertEqual(len(doc['global_object_lists'][0]['objects'][0]['display_data']), 1)
        self.assertFalse(doc['coverage']['runtime_display_semantics'])
        self.assertFalse(doc['coverage']['global_reference_resolution'])
        self.assertEqual(display.display_document(self.reader, project_bytes(repeated=True)), doc)

    def test_missing_image_or_late_bad_section_fails_before_write(self):
        for sections in [[image_section((3,))], [image_section(), struct.pack('<HH', 0, 3)]]:
            with self.subTest(sections=sections), tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'synthetic.cca'
                path.write_bytes(project_bytes(display_data(7, sections)))
                with patch.object(display.sys, 'argv', ['display', str(path), '--klikback-src',
                                                       os.environ['FF_KLIKBACK_SRC']]), \
                        patch.object(display, 'save_displays') as save, patch.object(project, 'report_fault') as report:
                    self.assertEqual(display.main(), 2)
                save.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_all_sections_source_words_and_independent_first_frame(self):
        from klikback.core.tgf.icon_census import display_first_frame
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        game = self.reader.read(raw)
        doc = display.display_document(self.reader, raw)
        pairs = [(s.data, out['objects'], True) for s, out in zip(
            [s for s in game.segments if s.ident == 6], doc['global_object_lists'])]
        self.assertEqual(len(doc['frames']), 13)
        for level, frame in zip(game.levels(), doc['frames']):
            pairs += [(b.data, out['objects'], False) for b, out in zip(
                [b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2], frame['object_lists'])]
        counts = collections.Counter()
        section_counts = collections.Counter()
        references = reference_only = 0
        for data, objects, global_list in pairs:
            parsed = self.reader.object_definitions(data, globals_have_blocks=global_list)
            self.assertEqual(len(parsed), len(objects))
            for obj, out in zip(parsed, objects):
                source_blocks = [b for b in obj.blocks if b.ident == 0] if obj.object_type in (5, 6, 7) else []
                self.assertEqual(len(source_blocks), len(out['display_data']))
                if obj.object_type in (5, 6, 7) and not source_blocks:
                    reference_only += 1
                for block, decoded in zip(source_blocks, out['display_data']):
                    source = block.data
                    counts[obj.object_type] += 1
                    self.assertEqual(bytes.fromhex(decoded['raw_hex']), source)
                    self.assertEqual(decoded['sha256'], hashlib.sha256(source).hexdigest())
                    self.assertEqual(decoded['object_list_offset'], block.offset)
                    rebuilt = bytes.fromhex(decoded['prefix_hex'])
                    if obj.object_type == 7:
                        length = int.from_bytes(source[46:48], 'little')
                        self.assertEqual(decoded['counter_attributes']['bytes'], length)
                        rebuilt += bytes.fromhex(decoded['counter_attributes']['raw_hex'])
                    for section in decoded['sections']:
                        at = len(rebuilt)
                        self.assertEqual(section['offset'], at)
                        length = int.from_bytes(source[at:at + 2], 'little')
                        mode = int.from_bytes(source[at + 2:at + 4], 'little')
                        section_counts[obj.object_type, mode, length] += 1
                        self.assertEqual(section['bytes'], length)
                        self.assertEqual(section['type_raw_u16'], mode)
                        rebuilt += bytes.fromhex(section['raw_hex'])
                        if mode in (1, 4):
                            count = int.from_bytes(source[at + 6:at + 8], 'little')
                            expected = [int.from_bytes(source[p:p + 2], 'little')
                                        for p in range(at + 8, at + 8 + count * 2, 2)]
                            self.assertEqual(section['image_ids'], expected)
                            self.assertEqual(len(section['image_bank_candidates']), count)
                            references += count
                            for image, candidates in zip(expected, section['image_bank_candidates']):
                                matching = [i for i, s in enumerate(game.segments) if s.ident == 10
                                            and image in [slot for slot, _, _ in self.reader.walk_bank(s.data)]]
                                self.assertEqual(candidates, matching)
                        else:
                            self.assertIsNone(section['image_ids'])
                    self.assertEqual(rebuilt, source)
                    oracle = display_first_frame(source, obj.object_type)
                    first = decoded['sections'][0]['image_ids']
                    self.assertEqual(first[0] if first else None, oracle)
        self.assertEqual(counts, {5: 4, 6: 2, 7: 21})
        self.assertEqual(section_counts, {(7, 0, 10): 13, (5, 1, 30): 8, (7, 1, 30): 6,
                                        (7, 3, 16): 2, (6, 4, 10): 2, (6, 1, 30): 2})
        self.assertEqual((references, reference_only), (178, 110))
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(display.display_document(self.reader, raw), doc)


if __name__ == '__main__':
    unittest.main()
