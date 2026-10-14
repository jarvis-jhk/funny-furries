import collections
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, project_index as project, export_project
from test_event_dump import record, row, event_block, global_block, reconstruct_program


def target_payload(target=0, tail=b''):
    return struct.pack('<H', target) + tail


def target_program(parameters):
    return row([record('condition', -3, -1, 0, parameters)],
               [record('action', -3, 2, 0, parameters)]) + bytes(2)


def target_project(parameters, tables):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    program = target_program(parameters)
    frame = bytes(0xB8) + block(0x8004, event_block(program))
    header = bytearray(0x16A)
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, 1)
    body = b''.join(block(7, data) for data in tables) + block(3, global_block(program))
    struct.pack_into('<I', header, 0x166, len(header) + len(body) + 6)
    return bytes(header) + body + block(0x8008, frame), program


class FrameTargetTests(unittest.TestCase):
    def test_exact_word_roles_boundaries_opaque_tails_and_lossless_bytes(self):
        for value in (0, 1, 13, 0x4000, 0xFFFE, 0xFFFF):
            payload = target_payload(value, b'\xffown\0tail')
            source = target_program([(26, payload), (999, payload)])
            for out in (events.decode_program(event_block(source)),
                        events.decode_global_program(global_block(source))):
                self.assertEqual(reconstruct_program(out), source)
                condition, action = out['rows'][0]['records']
                self.assertNotIn('frame_target_storage', condition['parameters'][0])
                a, unknown = action['parameters']
                self.assertEqual(a['payload_hex'], payload.hex())
                self.assertEqual(a['meaning'], 'unknown')
                self.assertEqual(a['frame_target_storage'], {
                    'payload_offset': 0, 'target_raw_u16': value,
                    'probe_method': 'raw_target_as_level_number_table_index',
                    'status': 'table_context_unresolved', 'candidates': [],
                    'runtime_resolution': 'unknown'})
                self.assertNotIn('frame_target_storage', unknown)

    def test_short_scalar_both_roles_refused_condition_has_no_frame_target(self):
        for payload in (b'', b'\xff'):
            with self.assertRaises(project.InputError):
                events.decode_rows(target_program([(26, payload)]))
            source = row([record('condition', -3, -1, 0, [(26, payload)])], []) + bytes(2)
            with self.assertRaises(project.InputError):
                events.decode_rows(source)
        source = row([record('condition', -3, -1, 0, [(26, bytes(2))])], []) + bytes(2)
        out = events.decode_rows(source)
        self.assertNotIn('frame_target_storage', out[0]['records'][0]['parameters'][0])


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class FrameTargetContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_nonidentity_word_probes_shared_frame_global_and_no_frame_guess(self):
        data = struct.pack('<HHHH', 3, 0xFFFF, 7, 1)
        raw, source = target_project([(26, target_payload(0)), (26, target_payload(1)),
                                      (26, target_payload(3)), (26, target_payload(4))], [data])
        doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 39)
        self.assertTrue(doc['coverage']['frame_target_storage'])
        self.assertFalse(doc['coverage']['frame_target_resolution'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        programs = doc['frames'][0]['programs'] + doc['global_events']
        refs = []
        for p in programs:
            self.assertEqual(reconstruct_program(p), source)
            refs.append([p['frame_target_storage'] for p in p['rows'][0]['records'][1]['parameters']])
        self.assertEqual(refs[0], refs[1])
        self.assertEqual([r['status'] for r in refs[0]], ['table_slot_probe'] * 3 + ['table_slot_unavailable'])
        self.assertEqual([r['candidates'][0]['raw_u16'] for r in refs[0][:3]], [3, 0xFFFF, 1])
        self.assertEqual(refs[0][2]['candidates'], [{'segment_id': 0, 'slot_id': 3, 'payload_offset': 6, 'raw_u16': 1}])
        self.assertTrue(all('frame_id' not in c for r in refs[0] for c in r['candidates']))
        table = doc['level_number_storage'][0]
        self.assertEqual(table['raw_hex'], data.hex())
        self.assertEqual(table['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual([w['raw_u16'] for w in table['words']], [3, 0xFFFF, 7, 1])
        self.assertEqual(events.event_document(self.reader, raw), doc)
        lines = events.readable(doc).splitlines()
        self.assertEqual(sum(l.startswith('          FRAME_TARGET ') for l in lines), 8)
        self.assertEqual(sum(l.startswith('LEVEL_NUMBER_STORAGE ') for l in lines), 1)

    def test_absent_empty_duplicate_odd_tables_no_sentinel_and_lossless_views(self):
        for tables in ([], [b''], [b'\xff'], [b'\xff\xff\x80'], [b'\x03\0', b'\x04\0']):
            raw, _ = target_project([(26, target_payload())], tables)
            doc = events.event_document(self.reader, raw)
            ref = doc['global_events'][0]['rows'][0]['records'][1]['parameters'][0]['frame_target_storage']
            self.assertEqual(ref['runtime_resolution'], 'unknown')
            self.assertEqual(ref['status'], 'table_slot_unavailable' if not any(len(t) >= 2 for t in tables)
                             else 'ambiguous_table_slot_probes' if len(tables) == 2 else 'table_slot_probe')
            if len(tables) == 2:
                self.assertEqual(ref['candidates'], [
                    {'segment_id': 0, 'slot_id': 0, 'payload_offset': 0, 'raw_u16': 3},
                    {'segment_id': 1, 'slot_id': 0, 'payload_offset': 0, 'raw_u16': 4}])
            for data, table in zip(tables, doc['level_number_storage']):
                reconstructed = b''.join(struct.pack('<H', w['raw_u16']) for w in table['words'])
                reconstructed += bytes.fromhex(table['suffix_hex'])
                self.assertEqual(reconstructed, data)
                self.assertEqual(bytes.fromhex(table['raw_hex']), data)
        raw, _ = target_project([(26, target_payload(0xFFFF))], [b'\0\0'])
        out = events.event_document(self.reader, raw)['global_events'][0]['rows'][0]['records'][1]['parameters'][0]
        self.assertEqual(out['frame_target_storage']['status'], 'table_slot_unavailable')
        self.assertEqual(out['frame_target_storage']['candidates'], [])
        raw, _ = target_project([(26, target_payload(0xFFFF))], [bytes(2 * 0xFFFF) + b'\x07\0'])
        out = events.event_document(self.reader, raw)['global_events'][0]['rows'][0]['records'][1]['parameters'][0]
        self.assertEqual(out['frame_target_storage']['status'], 'table_slot_probe')
        self.assertEqual(out['frame_target_storage']['candidates'], [
            {'segment_id': 0, 'slot_id': 0xFFFF, 'payload_offset': 2 * 0xFFFF, 'raw_u16': 7}])

    def test_external_converter_changes_only_action_target_word(self):
        from klikback.core.common import reconstruct_event_test as converter
        for value in (0, 13, 0xFFFE, 0xFFFF):
            source = target_program([(26, target_payload(value, b'own tail')), (999, b'own bytes')])[:-2]
            mapped = converter.compiled_event_to_editor_event(source, frame_target_map={value: 101})
            a, b = events.decode_rows(source + bytes(2))[0], events.decode_rows(mapped + bytes(2))[0]
            self.assertEqual(a['records'][0]['parameters'], b['records'][0]['parameters'])
            old, new = a['records'][1]['parameters'], b['records'][1]['parameters']
            self.assertEqual(new[0]['payload_hex'], target_payload(101, b'own tail').hex())
            self.assertEqual(new[1], old[1])
            self.assertEqual(old[0]['frame_target_storage']['target_raw_u16'], value)
            self.assertEqual(new[0]['frame_target_storage']['target_raw_u16'], 101)

    def test_late_short_target_refused_before_json_text_bundle_or_reporting(self):
        raw, _ = target_project([(26, target_payload(7, b'own tail'))], [])
        old = record('action', -3, 2, 0, [(26, target_payload(7, b'own tail'))])
        new = record('action', -3, 2, 0, [(26, b'\xff'), (999, b'own!!')])
        self.assertEqual(len(new), len(old))
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
                save.assert_not_called()
                bundle.assert_not_called()
                report.assert_not_called()

    def test_bundle_annotations_atomic_repeat_and_table_storage(self):
        raw, _ = target_project([(26, target_payload())], [b'\x07\0'])
        manifest, files = export_project.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(events.event_document(self.reader, raw)))
        self.assertIn(b'FRAME_TARGET ', files['events.txt'])
        self.assertIn(b'LEVEL_NUMBER_STORAGE ', files['events.txt'])
        self.assertEqual(manifest['components']['events.json'], {'exporter': 'event-dump/39', 'schema_version': 39})
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = export_project.save_bundle(manifest, files, Path(scratch))
            self.assertEqual(export_project.save_bundle(manifest, files, Path(scratch)), target)
            self.assertTrue(all((target / name).read_bytes() == data for name, data in files.items()))
        self.assertEqual(export_project.research_bundle(self.reader, raw), (manifest, files))

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_word_tables_external_converter_and_lossless_programs(self):
        from klikback.core.common import reconstruct_event_test as converter
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        original = [(i, s) for i, s in enumerate(self.reader.read(raw).segments) if s.ident == 7]
        self.assertEqual(len(original), 1)
        table_words = []
        for table, (i, s) in zip(doc['level_number_storage'], original):
            self.assertEqual(table['segment_id'], i)
            self.assertEqual(table['offset'], s.offset)
            self.assertEqual(bytes.fromhex(table['raw_hex']), s.data)
            direct = [int.from_bytes(s.data[n:n + 2], 'little') for n in range(0, len(s.data) - 1, 2)]
            self.assertEqual([w['raw_u16'] for w in table['words']], direct)
            table_words.extend(direct)
        self.assertEqual(table_words, [4, 3, 0, 2, 5, 6, 7, 8, 9, 12, 10, 11, 0xFFFF, 1])
        programs = []
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for p in frame['programs']:
                data = blocks[p['block_id']].data
                programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        segments = self.reader.read(raw).segments
        for p in doc['global_events']:
            data = segments[p['segment_id']].data
            programs.append((p, data[p['program_offset']:p['program_offset'] + p['program_bytes']]))
        counts = collections.Counter()
        probes = 0
        for p, source in programs:
            self.assertEqual(reconstruct_program(p), source)
            for r in p['rows']:
                affected = []
                for rec in r['records']:
                    for param in rec['parameters']:
                        if param['type'] != 26 or rec['role'] != 'action':
                            self.assertNotIn('frame_target_storage', param)
                            continue
                        target = param['frame_target_storage']
                        at = param['offset'] + 4
                        word = int.from_bytes(source[at:at + 2], 'little')
                        self.assertEqual(target['target_raw_u16'], word)
                        self.assertEqual(word, 13)
                        expected = [{'segment_id': i, 'slot_id': word, 'payload_offset': 2 * word,
                                     'raw_u16': int.from_bytes(s.data[2 * word:2 * word + 2], 'little')}
                                    for i, s in original if 2 * word + 2 <= len(s.data)]
                        self.assertEqual(target['candidates'], expected)
                        self.assertEqual(target['status'], 'table_slot_probe')
                        self.assertEqual(target['runtime_resolution'], 'unknown')
                        affected.append(param)
                        counts[(rec['object_type'], rec['opcode'])] += 1
                if affected:
                    chunk = source[r['offset']:r['offset'] + r['bytes']]
                    mapped = converter.compiled_event_to_editor_event(chunk, frame_target_map={13: 101})
                    out = events.decode_rows(mapped + bytes(2))[0]
                    new = [param for rec in out['records'] if rec['role'] == 'action'
                           for param in rec['parameters'] if param['type'] == 26]
                    self.assertEqual(len(new), len(affected))
                    for a, b in zip(affected, new):
                        self.assertEqual(b['payload_hex'], (b'\x65\0' + bytes.fromhex(a['payload_hex'])[2:]).hex())
                    probes += 1
        self.assertEqual(counts, {(-3, 2): 2})
        self.assertEqual(probes, 2)
        self.assertEqual(path.read_bytes(), raw)
        print('Original frame-target parameters: 2; target13/table slot13 word1; external converter rows:', probes)


if __name__ == '__main__':
    unittest.main()
