import collections
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import event_dump as events, project_index as project, export_project
from test_event_dump import record, row, event_block, global_block, reconstruct_program
from test_event_groups import opening, closing


def payload(key=7, runtime=0xDEADBEEF, tail=b''):
    return struct.pack('<IH', runtime, key) + tail


def ordinary(value):
    return row([record('condition', -1, -12, 0, [(39, value)])],
               [record('action', -1, 3, 0, [(39, value)])])


def project_bytes(value=payload()):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    global_source = opening(b'global\n"name"', (18, 7)) + closing() + ordinary(value) + bytes(2)
    frame_source = opening(b'local', (2, 7)) + closing() + ordinary(value) + bytes(2)
    # Repeated frame programs stay separate; a second frame has no local group.
    frames = [bytes(0xB8) + block(4, event_block(frame_source)) + block(0x8004, event_block(frame_source)),
              bytes(0xB8) + block(0x8004, event_block(ordinary(value) + bytes(2)))]
    header = bytearray(0x166 + 4 * len(frames))
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, len(frames))
    body = block(3, global_block(global_source))
    for i, frame in enumerate(frames):
        struct.pack_into('<I', header, 0x166 + 4 * i, len(header) + len(body) + 6)
        body += block(0x8008 if i == len(frames) - 1 else 8, frame)
    return bytes(header) + body


def targets(doc):
    for program in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
        for r in program['rows']:
            for rec in r['records']:
                for p in rec['parameters']:
                    if p['type'] == 39:
                        yield program, rec, p, p['group_parameter_storage']


class GroupParameterTests(unittest.TestCase):
    def test_word_boundaries_roles_tail_and_lossless_storage(self):
        for key in (0, 7, 0x4000, 0xFFFF):
            for runtime in (0, 0xDEADBEEF, 0xFFFFFFFF):
                value = payload(key, runtime, b'\xFFown\0tail')
                source = ordinary(value) + bytes(2)
                for doc in (events.decode_program(event_block(source)), events.decode_global_program(global_block(source))):
                    self.assertEqual(reconstruct_program(doc), source)
                    for rec in doc['rows'][0]['records']:
                        p = rec['parameters'][0]
                        self.assertEqual(p['payload_hex'], value.hex())
                        self.assertEqual(p['meaning'], 'unknown')
                        self.assertEqual(p['group_parameter_storage'], {
                            'runtime_raw_u32': runtime, 'key_raw_u16': key, 'suffix_hex': value[6:].hex(),
                            'status': 'program_context_unresolved', 'candidates': []})

    def test_short_runtime_refused_partial_key_preserved_unknown_type_untouched(self):
        for size in range(4):
            with self.assertRaises(project.InputError):
                events.decode_rows(ordinary(bytes(size)) + bytes(2))
        for value in (bytes(4), bytes(4) + b'\xFF'):
            p = events.decode_group_parameter(value)
            self.assertIsNone(p['key_raw_u16'])
            self.assertEqual(p['suffix_hex'], value[4:].hex())
        doc = events.decode_rows(row([], [record('action', -1, 3, 0, [(999, bytes(3))])]) + bytes(2))
        self.assertNotIn('group_parameter_storage', doc[0]['records'][0]['parameters'][0])


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class GroupParameterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_scope_equality_ambiguity_names_and_repeat(self):
        raw = project_bytes()
        doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 28)
        self.assertTrue(doc['coverage']['group_parameter_stored_word_candidates'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        ts = list(targets(doc))
        self.assertEqual(len(ts), 8)
        self.assertEqual([t['status'] for _, _, _, t in ts], ['ambiguous_stored_word'] * 4 + ['stored_word_candidate'] * 4)
        for (_, _, _, t), block_id in zip(ts[:4], (0, 0, 1, 1)):
            self.assertEqual([c['scope'] for c in t['candidates']], ['frame', 'global'])
            self.assertEqual(t['candidates'][0]['block_id'], block_id)
            self.assertEqual(t['candidates'][0]['frame_id'], 0)
            self.assertEqual(t['candidates'][1]['segment_id'], 0)
        lines = [s for s in events.readable(doc).splitlines() if s.startswith('          GROUP_PARAMETER ')]
        self.assertEqual(len(lines), 8)
        self.assertTrue(all('\n' not in s for s in lines))
        self.assertIn('global\\n\\"name\\"', lines[0])
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_missing_keys_unclosed_duplicates_unknown_titles_no_sentinels(self):
        for value, status in [(bytes(4), 'no_key_word'), (payload(0), 'no_stored_word_match'),
                              (payload(0xFFFF), 'no_stored_word_match')]:
            doc = events.event_document(self.reader, project_bytes(value))
            self.assertTrue(all(t['status'] == status and t['candidates'] == [] for _, _, _, t in targets(doc)))
        source = opening(b'A', (2, 7)) + opening(b'B', (2, 7)) + ordinary(payload()) + bytes(2)
        program = events.decode_program(event_block(source))
        scope = {'frames': [{'id': 0, 'programs': [{'block_id': 2, **program}]}], 'global_events': []}
        events.annotate_group_parameters(scope)
        for _, _, _, target in targets(scope):
            self.assertEqual(target['status'], 'ambiguous_stored_word')
            self.assertEqual([c['row_id'] for c in target['candidates']], [0, 1])
            self.assertEqual([c['matching_row_id'] for c in target['candidates']], [None, None])
        unknown = events.decode_program(event_block(row([record('condition', -1, -10, 0, [(38, b'')])], []) + ordinary(payload()) + bytes(2)))
        scope['frames'][0]['programs'] = [{'block_id': 0, **unknown}]
        events.annotate_group_parameters(scope)
        self.assertTrue(all(t['status'] == 'no_stored_word_match' for _, _, _, t in targets(scope)))

    def test_multiple_global_segments_and_zero_key_remain_explicit(self):
        globals_ = []
        for segment_id, name in [(2, b'Zero A'), (9, b'Zero B')]:
            program = events.decode_global_program(global_block(
                opening(name, (0xFFFF, 0)) + closing() + ordinary(payload(0)) + bytes(2)))
            globals_.append({"segment_id": segment_id, **program})
        frame = events.decode_program(event_block(ordinary(payload(0)) + bytes(2)))
        doc = {'frames': [{'id': 4, 'programs': [{'block_id': 6, **frame}]}], 'global_events': globals_}
        events.annotate_group_parameters(doc)
        for _, _, _, target in targets(doc):
            self.assertEqual(target['status'], 'ambiguous_stored_word')
            self.assertEqual([c['segment_id'] for c in target['candidates']], [2, 9])
            self.assertEqual([c['key_raw_u16'] for c in target['candidates']], [0, 0])
            self.assertEqual([c['row_id'] for c in target['candidates']], [0, 0])

    def test_external_converter_clears_only_action_runtime_word(self):
        from klikback.core.common import reconstruct_event_test as converter
        source = ordinary(payload(7, tail=b'own tail'))
        changed = converter.compiled_event_to_editor_event(source)
        a, b = events.decode_rows(source + bytes(2))[0], events.decode_rows(changed + bytes(2))[0]
        for old, new in zip(a['records'], b['records']):
            op, np = old['parameters'][0], new['parameters'][0]
            expected = bytearray.fromhex(op['payload_hex'])
            if old['role'] == 'action':
                expected[:4] = bytes(4)
            self.assertEqual(np['payload_hex'], expected.hex())
            self.assertEqual(np['group_parameter_storage']['key_raw_u16'], 7)

    def test_late_invalid_before_writes_reporting_and_bundle_repeat(self):
        raw = project_bytes()
        old = record('action', -1, 3, 0, [(39, payload())])
        new = record('action', -1, 3, 0, [(39, bytes(2)), (999, b'')])
        self.assertEqual(len(old), len(new))
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        bad = raw[:at] + new + raw[at + len(old):]
        for module, flags in [(events, []), (events, ['--text']), (export_project, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(export_project, 'save_bundle') as bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); bundle.assert_not_called(); report.assert_not_called()
        manifest, files = export_project.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(events.event_document(self.reader, raw)))
        self.assertIn(b'GROUP_PARAMETER', files['events.txt'])
        self.assertEqual(manifest['components']['events.json'], {'exporter': 'event-dump/28', 'schema_version': 28})
        self.assertEqual(export_project.research_bundle(self.reader, raw), (manifest, files))

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_words_candidate_keys_converter_and_lossless_bytes(self):
        from klikback.core.common import reconstruct_event_test as converter
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        counts = collections.Counter()
        # Independent candidate table from raw opening parameters, not annotation titles.
        def table(program, scope):
            out = []
            source = reconstruct_program(program)
            for r in program['rows']:
                row_bytes = source[r['offset']:r['offset'] + r['bytes']]
                if converter.group_marker(row_bytes) != 1:
                    continue
                for p in r['records'][0]['parameters']:
                    if p['type'] == 38 and p['bytes'] == 88:
                        start = p['offset'] + 4
                        key = int.from_bytes(source[start + 2:start + 4], 'little')
                        out.append((scope, r['id'], key, source[start + 4:start + 84]))
            return out
        global_table = [c for p in doc['global_events'] for c in table(p, ('global', p['segment_id']))]
        contexts = {}
        for f in doc['frames']:
            for p in f['programs']:
                contexts[id(p)] = table(p, ('frame', f['id'], p['block_id'])) + global_table
        probes = set()
        for program, rec, p, out in targets(doc):
            source = reconstruct_program(program)
            start = p['offset'] + 4
            self.assertEqual(out['runtime_raw_u32'], int.from_bytes(source[start:start + 4], 'little'))
            key = int.from_bytes(source[start + 4:start + 6], 'little')
            self.assertEqual(out['key_raw_u16'], key)
            self.assertEqual(out['suffix_hex'], source[start + 6:p['offset'] + p['bytes']].hex())
            expected = [(scope, rid, field) for scope, rid, k, field in contexts.get(id(program), global_table) if k == key]
            actual = [(('frame', c['frame_id'], c['block_id']) if c['scope'] == 'frame' else ('global', c['segment_id']),
                       c['row_id'], bytes.fromhex(c['title']['field_hex'])) for c in out['candidates']]
            self.assertEqual(actual, expected)
            counts[(rec['role'], out['status'])] += 1
            self.assertEqual(bytes.fromhex(p['payload_hex']), source[start:p['offset'] + p['bytes']])
            # Check real converter actions against raw source; rows without actions
            # are outside that experiment's contract and are not claimed as probes.
            r = next(r for r in program['rows'] if rec in r['records'])
            if r['condition_count'] and r['action_count'] and (id(program), r['id']) not in probes:
                converted = converter.compiled_event_to_editor_event(source[r['offset']:r['offset'] + r['bytes']])
                decoded = events.decode_rows(converted + bytes(2))[0]
                for record_ in decoded['records']:
                    for param in record_['parameters']:
                        if param['type'] == 39 and record_['role'] == 'action':
                            self.assertEqual(param['group_parameter_storage']['runtime_raw_u32'], 0)
                probes.add((id(program), r['id']))
        self.assertEqual(sum(counts.values()), 159)
        self.assertEqual(path.read_bytes(), raw)
        self.assertGreater(len(probes), 0)
        print('Original group parameters:', dict(counts), 'converter row probes:', len(probes))


if __name__ == '__main__':
    unittest.main()
