import copy
import importlib
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import event_dump as events
from tools import project_index as project
from test_event_dump import event_block, record, row, reconstruct_program


def object_entry(slot, name='own synthetic name', kind=2, **changes):
    return {'id': slot, 'name': name, 'type': kind, 'type_name': 'active',
            'global': False, 'deleted': False, **changes}


def annotation(kind, reference, lists):
    return events.reference_annotation({'object_type': kind, 'object_reference': reference}, lists)


def synthetic_references():
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data

    def objects(name):
        header = bytearray(68)
        header[:len(name)] = name
        header[0x26] = 0x80  # Reference-only global-flagged local definition.
        header[0x2A] = 2
        return struct.pack('<I', 1) + header

    program = row([record('condition', 2, -17, 0, [(999, b'own bytes')])],
                  [record('action', 2, 99, 0, [])]) + bytes(2)
    frames = [bytes(0xB8) + block(2, objects(b'first')) + block(0x8004, event_block(program)),
              bytes(0xB8) + block(2, objects(b'second')) + block(0x8004, event_block(program)),
              bytes(0xB8) + block(0x8004, event_block(program)),
              bytes(0xB8) + block(2, objects(b'one')) + block(2, objects(b'two'))
              + block(0x8004, event_block(program))]
    header = bytearray(0x166 + 4 * len(frames))
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, len(frames))
    body = b''
    for i, frame in enumerate(frames):
        struct.pack_into('<I', header, 0x166 + 4 * i, len(header) + len(body) + 6)
        body += block(0x8008 if i == len(frames) - 1 else 8, frame)
    return bytes(header) + body, program


class AnnotationTests(unittest.TestCase):
    def test_local_slot_match_retains_name_type_flags_and_block_identity(self):
        obj = object_entry(3, 'line\nbreak "quoted"')
        obj['global'] = True
        result = annotation(2, 3, [(7, [object_entry(0), obj])])
        self.assertEqual(result, {'reference_raw_u16': 3, 'status': 'local_slot_match',
                                  'candidates': [{'block_id': 7, **obj}]})
        self.assertEqual(obj['name'], 'line\nbreak "quoted"')

    def test_non_object_and_encoded_references_never_guess_a_slot(self):
        lists = [(1, [object_entry(0), object_entry(0x4000), object_entry(0x8000)])]
        for kind in [0, -1, -2, -3, -4, -5, -6, -7, -128]:
            result = annotation(kind, 0, lists)
            self.assertEqual(result['status'], 'non_object_type')
            self.assertEqual(result['candidates'], [])
        for reference in [0x4000, 0x4001, 0x7FFF, -32768, -1]:
            result = annotation(2, reference, lists)
            self.assertEqual(result['reference_raw_u16'], reference & 0xFFFF)
            self.assertEqual(result['status'], 'encoded_reference_unresolved')
            self.assertEqual(result['candidates'], [])

    def test_upper_plain_reference_and_extension_type_are_not_compacted(self):
        result = annotation(32, 0x3FFF, [(9, [object_entry(0), object_entry(0x3FFF, kind=32)])])
        self.assertEqual(result['status'], 'local_slot_match')
        self.assertEqual(result['candidates'][0]['id'], 0x3FFF)
        self.assertEqual(result['candidates'][0]['type'], 32)
        self.assertEqual(annotation(32, 0x3FFE, [(9, [object_entry(0x3FFF, kind=32)])])['status'],
                         'missing_local_slot')

    def test_missing_deleted_mismatched_and_ambiguous_keep_evidence(self):
        cases = [([], 'missing_local_slot', 0),
                 ([(2, [object_entry(0, kind=255, deleted=True)])], 'deleted_local_slot', 1),
                 ([(2, [object_entry(0, kind=7)])], 'type_mismatch', 1),
                 ([(2, [object_entry(0)]), (4, [object_entry(0, kind=7)])],
                  'ambiguous_local_slot', 2)]
        for lists, status, count in cases:
            with self.subTest(status=status):
                before = copy.deepcopy(lists)
                result = annotation(2, 0, lists)
                self.assertEqual(result['status'], status)
                self.assertEqual(len(result['candidates']), count)
                self.assertEqual(lists, before)
        result = annotation(2, 0, cases[-1][0])
        self.assertEqual([o['block_id'] for o in result['candidates']], [2, 4])
        self.assertEqual([o['type'] for o in result['candidates']], [2, 7])

    def test_readable_names_escape_newlines_and_opcode_meanings_stay_unknown(self):
        program = events.decode_program(event_block(row([], [record('action', 2, 99, 0, [])]) + bytes(2)))
        rec = program['rows'][0]['records'][0]
        rec['object_reference_annotation'] = annotation(2, 0, [(1, [object_entry(0, 'name\n"quote"')])])
        lines = events.readable_program(program)
        target = next(line for line in lines if 'REFERENCE status=' in line)
        self.assertNotIn('\n', target)
        self.assertIn('name\\n\\"quote\\"', target)
        self.assertEqual(rec['meaning'], 'unknown')
        self.assertIn('opcode=99 reference=0 meaning=UNKNOWN', '\n'.join(lines))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ReferenceContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_scope_missing_and_repeated_lists_and_lossless_program(self):
        raw, program = synthetic_references()
        document = events.event_document(self.reader, raw)
        self.assertEqual(document['schema_version'], 17)
        targets = []
        for frame in document['frames']:
            block = frame['programs'][0]
            self.assertEqual(reconstruct_program(block), program)
            self.assertEqual([r['opcode'] for r in block['rows'][0]['records']], [-17, 99])
            targets.append(block['rows'][0]['records'][0]['object_reference_annotation'])
        self.assertEqual([t['status'] for t in targets],
                         ['local_slot_match', 'local_slot_match', 'missing_local_slot', 'ambiguous_local_slot'])
        self.assertEqual([t['candidates'][0]['name'] for t in targets[:2]], ['first', 'second'])
        self.assertTrue(targets[0]['candidates'][0]['global'])
        self.assertEqual([o['block_id'] for o in targets[3]['candidates']], [0, 1])
        self.assertEqual([o['name'] for o in targets[3]['candidates']], ['one', 'two'])
        self.assertFalse(document['coverage']['global_reference_resolution'])
        self.assertEqual(events.event_document(self.reader, raw), document)

    def test_invalid_later_program_writes_nothing_and_reports_no_fault(self):
        raw, _ = synthetic_references()
        raw = raw[:-5]  # Truncate the last event auxiliary block/container.
        with patch.object(events.sys, 'argv', ['events', 'unused', '--klikback-src', 'unused']), \
                patch.object(project, 'load_reader', return_value=self.reader), \
                patch.object(Path, 'read_bytes', return_value=raw), \
                patch.object(project, 'save_export') as save, patch.object(project, 'report_fault') as report:
            self.assertEqual(events.main(), 2)
            save.assert_not_called()
            report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_local_slots_against_external_objects_columns_and_source_words(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        document = events.event_document(self.reader, raw)
        external = importlib.import_module('klikback.core.tgf.block3')
        counts = {}
        for frame, level in zip(document['frames'], self.reader.read(raw).levels()):
            _, blocks = self.reader.level_blocks(level.data)
            objects = [(i, self.reader.object_definitions(b.data))
                       for i, b in enumerate(blocks) if b.ident == 2]
            for program in frame['programs']:
                source = blocks[program['block_id']].data
                start = program['program_offset']
                event_bytes = source[start:start + program['program_bytes']]
                seen = []
                columns = external.columns_from_events(objects[0][1] if objects else [], event_bytes)
                for event_row in program['rows']:
                    for rec in event_row['records']:
                        offset = start + rec['offset']
                        kind, _, reference = struct.unpack_from('<bbh', source, offset + 2)
                        target = rec['object_reference_annotation']
                        self.assertEqual(rec['object_reference'], reference)
                        if reference not in seen:
                            seen.append(reference)
                        expected = [{'block_id': block_id, 'id': o.index, 'name': o.name,
                                     'type': o.object_type, 'type_name': o.type_name,
                                     'global': o.is_global, 'deleted': o.deleted}
                                    for block_id, entries in objects for o in entries
                                    if o.index == reference] if kind > 0 and 0 <= reference < 0x4000 else []
                        self.assertEqual(target['candidates'], expected)
                        counts[target['status']] = counts.get(target['status'], 0) + 1
                        if target['status'] == 'local_slot_match':
                            self.assertEqual(expected[0]['type'], kind)
                            if kind not in external.UNCOLUMNED_TYPES:
                                self.assertIn((kind, reference), columns)
                self.assertEqual(seen, external.referenced_objects(event_bytes))
                self.assertEqual(reconstruct_program(program), event_bytes)
        self.assertEqual(counts, {'local_slot_match': 4613, 'non_object_type': 2958,
                                  'encoded_reference_unresolved': 2})
        self.assertTrue(all('object_reference_annotation' not in r
                            for p in document['global_events'] for row_ in p['rows'] for r in row_['records']))
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
