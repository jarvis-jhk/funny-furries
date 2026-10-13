import collections
import os
from pathlib import Path
import struct
import unittest

from tools import event_dump as events
from tools import project_index as project
from test_event_dump import record, row, event_block, global_block, reconstruct_program


def opening(name=b'Our group', prefix=(0xF123, 0xFEDC), extra_parameters=()):
    payload = struct.pack('<HH', *prefix) + name.ljust(80, b'\0')
    return row([record('condition', -1, -10, 0, [(38, payload), *extra_parameters])], [])


def closing():
    return row([record('condition', -1, -11, 0, [])], [])


def ordinary():
    return row([record('condition', 2, -10, 0, [])], [])


class GroupTests(unittest.TestCase):
    def test_nested_pairs_scope_order_and_lossless_frame_global(self):
        raw = opening(b'Parent') + ordinary() + opening(b'Child') + ordinary() + closing() + closing() + ordinary() + bytes(2)
        for document in (events.decode_program(event_block(raw)),
                         events.decode_global_program(global_block(raw))):
            with self.subTest(header=document['header_hex']):
                self.assertEqual(reconstruct_program(document), raw)
                self.assertEqual(document['event_groups'], {
                    'status': 'balanced', 'open_row_ids': [0, 2],
                    'unclosed_open_row_ids': [], 'unmatched_close_row_ids': []})
                annotations = [r['event_group_annotation'] for r in document['rows']]
                self.assertEqual([a['kind'] for a in annotations], ['open', 'event', 'open', 'event', 'close', 'close', 'event'])
                self.assertEqual([a['enclosing_open_row_ids'] for a in annotations], [[], [0], [0], [0, 2], [0], [], []])
                self.assertEqual([a['matching_row_id'] for a in annotations], [5, None, 4, None, 2, 0, None])
                self.assertEqual(annotations[0]['title']['byte_view_latin1'], 'Parent')
                self.assertEqual(annotations[2]['title']['byte_view_latin1'], 'Child')
                self.assertEqual(annotations[0]['title']['prefix_raw_u16'], [0xF123, 0xFEDC])
                self.assertEqual(document['rows'][0]['records'][0]['meaning'], 'unknown')
                self.assertEqual(document['rows'][0]['records'][0]['parameters'][0]['meaning'], 'unknown')

    def test_title_bytes_nul_tail_full_field_and_readable_escaping(self):
        for name in [b'', b'A\0nonzero tail', b'\xff\x80"\nROW 99', bytes(range(1, 81))]:
            raw = opening(name) + closing() + bytes(2)
            doc = events.decode_program(event_block(raw))
            title = doc['rows'][0]['event_group_annotation']['title']
            self.assertEqual(bytes.fromhex(title['field_hex']), name.ljust(80, b'\0'))
            self.assertEqual(bytes.fromhex(title['bytes_hex']), name.split(b'\0')[0])
            self.assertEqual(title['byte_view_latin1'].encode('latin1'), name.split(b'\0')[0])
            self.assertEqual(title['source_encoding'], 'unknown')
            lines = events.readable_program(doc)
            self.assertEqual(len([line for line in lines if line.startswith('      GROUP ')]), 2)
            self.assertTrue(all('\n' not in line for line in lines))
            self.assertEqual(reconstruct_program(doc), raw)

    def test_unknown_title_shapes_are_preserved_without_guessing(self):
        for parameters in [[], [(38, b'')], [(38, bytes(83))], [(38, bytes(85))],
                           [(38, bytes(84)), (38, bytes(84))], [(999, bytes(84))]]:
            with self.subTest(parameters=parameters):
                raw = row([record('condition', -1, -10, 0, parameters)], []) + closing() + bytes(2)
                doc = events.decode_program(event_block(raw))
                self.assertIsNone(doc['rows'][0]['event_group_annotation']['title'])
                self.assertEqual(doc['event_groups']['status'], 'balanced')
                self.assertEqual(reconstruct_program(doc), raw)
        raw = opening(extra_parameters=[(999, b'opaque')]) + closing() + bytes(2)
        self.assertEqual(events.decode_rows(raw)[0]['event_group_annotation']['title']['parameter_id'], 0)

    def test_only_first_system_condition_is_a_group_marker(self):
        raw = ordinary()
        raw += row([], [record('action', -1, -10, 0, [(38, bytes(84))])])
        raw += row([record('condition', 2, 0, 0, []), record('condition', -1, -10, 0, [])], [])
        raw += row([record('condition', -2, -11, 0, [])], []) + bytes(2)
        doc = events.decode_program(event_block(raw))
        self.assertEqual(doc['event_groups']['open_row_ids'], [])
        self.assertTrue(all(r['event_group_annotation']['kind'] == 'event' for r in doc['rows']))
        self.assertEqual(reconstruct_program(doc), raw)

    def test_unbalanced_groups_remain_explicit_and_each_program_is_separate(self):
        raw = closing() + opening(b'Unclosed') + ordinary() + bytes(2)
        doc = events.decode_program(event_block(raw))
        self.assertEqual(doc['event_groups'], {'status': 'unbalanced', 'open_row_ids': [1],
                                             'unclosed_open_row_ids': [1], 'unmatched_close_row_ids': [0]})
        self.assertEqual(doc['rows'][2]['event_group_annotation']['enclosing_open_row_ids'], [1])
        self.assertEqual(reconstruct_program(doc), raw)
        other = events.decode_global_program(global_block(closing() + bytes(2)))
        self.assertEqual(other['event_groups']['unmatched_close_row_ids'], [0])
        self.assertEqual(other['event_groups']['open_row_ids'], [])
        self.assertEqual(events.decode_program(event_block(bytes(2)))['event_groups']['status'], 'balanced')

    def test_raw_group_words_do_not_determine_pairing(self):
        raw = opening(b'Same', (0, 7)) + closing() + opening(b'Same', (0, 7)) + closing() + bytes(2)
        doc = events.decode_program(event_block(raw))
        self.assertEqual([r['event_group_annotation']['matching_row_id'] for r in doc['rows']], [1, 0, 3, 2])
        self.assertEqual(doc['event_groups']['open_row_ids'], [0, 2])


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC') and os.environ.get('FF_TEST_PROJECT'),
                     'set FF_KLIKBACK_SRC and FF_TEST_PROJECT for original verification')
class OriginalGroups(unittest.TestCase):
    def test_original_names_pairing_source_words_external_helpers_and_lossless_bytes(self):
        reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))
        from klikback.core.common import global_event_reconstruct as independent
        from klikback.core.common import reconstruct_event_test as markers
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(reader, raw)
        programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
        counts = []
        names = collections.Counter()
        for program in programs:
            reconstructed = reconstruct_program(program)
            self.assertEqual(program['event_groups']['status'], 'balanced')
            stack = []
            opened = []
            for r in program['rows']:
                original_row = reconstructed[r['offset']:r['offset'] + r['bytes']]
                marker = markers.group_marker(original_row)
                annotation = r['event_group_annotation']
                self.assertEqual(annotation['kind'], {1: 'open', -1: 'close', 0: 'event'}[marker])
                if marker == 1:
                    opened.append(r['id'])
                    self.assertEqual(annotation['enclosing_open_row_ids'], stack)
                    stack.append(r['id'])
                    # Separate direct reads at row+28: u16 size/type, 4 opaque
                    # prefix bytes, then the 80-byte title field at row+36.
                    size, kind = struct.unpack_from('<HH', original_row, 28)
                    self.assertEqual((size, kind), (88, 38))
                    title = annotation['title']
                    self.assertEqual(title['field_hex'], original_row[36:116].hex())
                    self.assertEqual(title['prefix_raw_u16'], [int.from_bytes(original_row[32:34], 'little'),
                                                             int.from_bytes(original_row[34:36], 'little')])
                    names[title['byte_view_latin1']] += 1
                elif marker == -1:
                    self.assertTrue(stack)
                    start = stack.pop()
                    self.assertEqual(annotation['matching_row_id'], start)
                    self.assertEqual(program['rows'][start]['event_group_annotation']['matching_row_id'], r['id'])
                    self.assertEqual(annotation['enclosing_open_row_ids'], stack)
                else:
                    self.assertEqual(annotation['enclosing_open_row_ids'], stack)
            self.assertEqual(stack, [])
            self.assertEqual(program['event_groups']['open_row_ids'], opened)
            external = independent.group_records([reconstructed[r['offset']:r['offset'] + r['bytes']] for r in program['rows']])
            self.assertEqual([bytes.fromhex(program['rows'][i]['event_group_annotation']['title']['bytes_hex']) for i in opened],
                             [name for name, _word in external])
            counts.append(len(opened))
        self.assertEqual(counts, [0, 1] + [2] * 10 + [20])
        self.assertEqual(sum(counts), 41)
        self.assertEqual(names['Not Global'], 11)
        self.assertEqual(names['Bonus'], 10)
        for name in ['Keys Movement', 'Player 1', 'Player 2', 'Jetpack', 'Ice', 'Rockets', 'Explosions', 'Flame']:
            self.assertEqual(names[name], 1)
        self.assertTrue(doc['coverage']['editor_group_structure'])
        self.assertFalse(doc['coverage']['opcode_semantics'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
