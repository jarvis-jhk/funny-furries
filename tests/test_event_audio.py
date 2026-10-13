import collections
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import audio_dump, event_dump as events, project_index as project
from test_audio_dump import audio_record, bank, midi, pcm
from test_event_dump import event_block, global_block, record, row, reconstruct_program


def audio_program(parameters):
    return row([record('condition', -2, -1, 0, parameters)],
               [record('action', -2, 0, 0, parameters)]) + bytes(2)


def audio_project(parameters, banks):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    program = audio_program(parameters)
    frames = [bytes(184) + block(0x8004, event_block(program)) for _ in range(2)]
    segments = [(3, global_block(program))] + [(8, f) for f in frames] + banks
    header = bytearray(0x16E)
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, 2)
    body, frame_id = b'', 0
    for n, (kind, payload) in enumerate(segments):
        if kind == 8:
            struct.pack_into('<I', header, 0x166 + 4 * frame_id, len(header) + len(body) + 6)
            frame_id += 1
        body += block(kind | (0x8000 if n == len(segments) - 1 else 0), payload)
    return bytes(header) + body, program


def programs(document):
    return [p for f in document['frames'] for p in f['programs']] + document['global_events']


class AudioReferenceTests(unittest.TestCase):
    def test_both_types_roles_frame_global_and_opaque_tail_lossless(self):
        for kind in (6, 7):
            for handle in (0, 1, 0x3FFF, 0x4000, 0xFFFE, 0xFFFF):
                payload = struct.pack('<H', handle) + b'\xffopaque\0\n"tail"'
                raw = audio_program([(kind, payload)])
                for program in (events.decode_program(event_block(raw)), events.decode_global_program(global_block(raw))):
                    self.assertEqual(reconstruct_program(program), raw)
                    for rec in program['rows'][0]['records']:
                        param = rec['parameters'][0]
                        self.assertEqual(param['payload_hex'], payload.hex())
                        self.assertEqual(param['meaning'], 'unknown')
                        self.assertEqual(param['audio_reference_storage'], {
                            'kind': 'sound' if kind == 6 else 'music', 'payload_offset': 0,
                            'reference_raw_u16': handle, 'status': 'bank_context_unresolved', 'candidates': []})

    def test_minimal_handles_truncated_shapes_and_unknown_types(self):
        for kind in (6, 7):
            self.assertEqual(events.decode_audio_reference(bytes(2), kind)['reference_raw_u16'], 0)
            for payload in (b'', b'\0'):
                with self.assertRaises(project.InputError):
                    events.decode_rows(audio_program([(kind, payload)]))
        for kind in (0, 5, 8, 999):
            param = events.decode_rows(audio_program([(kind, b'')]))[0]['records'][0]['parameters'][0]
            self.assertNotIn('audio_reference_storage', param)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class AudioReferenceContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_kind_partition_gaps_application_scope_and_exported_media_identity(self):
        raw, original_program = audio_project([(6, struct.pack('<H', 0)), (7, struct.pack('<H', 2)),
                                               (6, struct.pack('<H', 1)), (7, struct.pack('<H', 0))],
                                              [(13, bank({0: pcm(), 2: pcm(b'own')})),
                                               (12, bank({2: audio_record(2, midi())}))])
        document = events.event_document(self.reader, raw)
        manifest, _ = audio_dump.audio_bundle(self.reader, raw)
        media = {(b['segment_id'], e['id']): (b['kind'], e) for b in manifest['banks'] for e in b['entries']}
        for program in programs(document):
            self.assertEqual(reconstruct_program(program), original_program)
            for rec in program['rows'][0]['records']:
                refs = [p['audio_reference_storage'] for p in rec['parameters']]
                self.assertEqual([r['status'] for r in refs], ['bank_slot_candidate'] * 2 + ['missing_bank_slot'] * 2)
                self.assertEqual([r['candidates'][0]['segment_id'] for r in refs[:2]], [3, 4])
                for ref in refs[:2]:
                    c = ref['candidates'][0]
                    kind, entry = media[c['segment_id'], c['id']]
                    self.assertEqual(c['kind'], kind)
                    for key in ('offset', 'bytes', 'record_sha256'):
                        self.assertEqual(c[key], entry[key])
        self.assertTrue(document['coverage']['audio_bank_reference_candidates'])
        self.assertFalse(document['coverage']['opcode_semantics'])
        self.assertEqual(document['schema_version'], 16)
        self.assertEqual(document['exporter'], 'event-dump/16')
        text = events.readable(document)
        self.assertEqual(text.count('          AUDIO_REFERENCE '), 24)
        self.assertEqual(events.event_document(self.reader, raw), document)

    def test_duplicate_empty_absent_banks_and_no_guessed_sentinels(self):
        parameters = [(6, struct.pack('<H', i)) for i in (0, 1, 0xFFFF)] + [(7, b'\xff\xff')]
        raw, _ = audio_project(parameters, [(13, bank({0: pcm()})), (13, bank({0: pcm(b'other'), 1: pcm()})),
                                            (12, bank({})), (13, bank({}))])
        doc = events.event_document(self.reader, raw)
        for program in programs(doc):
            refs = [p['audio_reference_storage'] for p in program['rows'][0]['records'][0]['parameters']]
            self.assertEqual([r['status'] for r in refs], ['ambiguous_bank_slot', 'bank_slot_candidate',
                                                         'missing_bank_slot', 'missing_bank_slot'])
            self.assertEqual([c['segment_id'] for c in refs[0]['candidates']], [3, 4])
            self.assertNotEqual(refs[0]['candidates'][0]['record_sha256'], refs[0]['candidates'][1]['record_sha256'])
            self.assertEqual(refs[1]['candidates'][0]['segment_id'], 4)
            self.assertEqual(refs[2]['reference_raw_u16'], 0xFFFF)
        absent, _ = audio_project(parameters, [])
        for program in programs(events.event_document(self.reader, absent)):
            self.assertTrue(all(p['audio_reference_storage']['status'] == 'missing_bank_slot'
                                for p in program['rows'][0]['records'][0]['parameters']))

    def test_pinned_converter_clears_only_exact_sound_music_handle_words(self):
        from klikback.core.common import reconstruct_event_test as oracle
        for kind in (6, 7):
            payload = b'\x34\x12\xff\x01opaque\0tail'
            raw = row([record('condition', -1, -1, 0, [])],
                      [record('action', -2, 0, 0, [(kind, payload)])])
            converted = oracle.compiled_event_to_editor_event(raw)
            target = events.decode_rows(raw + bytes(2))[0]['records'][1]['parameters'][0]['audio_reference_storage']
            self.assertEqual(target['reference_raw_u16'], 0x1234)
            self.assertEqual(target['payload_offset'], 0)
            at = 14 + 14 + 12 + 4
            expected = bytearray(raw)
            expected[at:at + 2] = b'\0\0' if kind == 6 else b'\xff\xff'
            self.assertEqual(converted, bytes(expected))

    def test_late_truncated_handle_refuses_json_text_bundle_before_save_or_report(self):
        from tools import export_project
        valid = [(6, b'\0\0'), (7, b'\x01\0')]
        raw, _ = audio_project(valid, [])
        old = record('action', -2, 0, 0, valid)
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        new = record('action', -2, 0, 0, [(6, b'\0\0x'), (7, b'\x01')])
        self.assertEqual(len(old), len(new))
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

    def test_combined_bundle_uses_same_candidates_and_keeps_media_bytes(self):
        from tools import export_project
        raw, _ = audio_project([(6, b'\0\0'), (7, b'\x02\0')],
                               [(13, bank({0: pcm()})), (12, bank({2: audio_record(2, midi())}))])
        manifest, files = export_project.research_bundle(self.reader, raw)
        doc = events.event_document(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(doc))
        self.assertEqual(files['events.txt'], events.readable(doc).encode())
        _, audio_files = audio_dump.audio_bundle(self.reader, raw)
        for name, data in audio_files.items():
            if name != 'manifest.json':
                self.assertEqual(files[name], data)
        with tempfile.TemporaryDirectory() as scratch:
            target = export_project.save_bundle(manifest, files, Path(scratch))
            self.assertEqual(export_project.save_bundle(manifest, files, Path(scratch)), target)
            self.assertEqual((target / 'events.json').read_bytes(), files['events.json'])

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_direct_bank_tables_handle_words_and_audio_manifest_agree(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        manifest, _ = audio_dump.audio_bundle(self.reader, raw)
        media = {(b['segment_id'], e['id']): (b['kind'], e) for b in manifest['banks'] for e in b['entries']}
        banks = []
        for segment_id, segment in enumerate(self.reader.read(raw).segments):
            if segment.ident not in (12, 13):
                continue
            count = int.from_bytes(segment.data[:4], 'little')
            entries = []
            for slot in range(count):
                start = int.from_bytes(segment.data[4 + 8 * slot:8 + 8 * slot], 'little')
                size = int.from_bytes(segment.data[8 + 8 * slot:12 + 8 * slot], 'little')
                if start:
                    entries.append({'segment_id': segment_id, 'id': slot,
                                    'kind': 'sound' if segment.ident == 13 else 'music',
                                    'offset': start, 'bytes': size,
                                    'record_sha256': hashlib.sha256(segment.data[start:start + size]).hexdigest()})
            banks += entries
        counts = collections.Counter()
        for program in programs(doc):
            source = reconstruct_program(program)
            for event_row in program['rows']:
                for rec in event_row['records']:
                    for param in rec['parameters']:
                        if param['type'] not in (6, 7):
                            self.assertNotIn('audio_reference_storage', param)
                            continue
                        counts[param['type']] += 1
                        at = param['offset'] + 4
                        handle = int.from_bytes(source[at:at + 2], 'little')
                        ref = param['audio_reference_storage']
                        kind = 'sound' if param['type'] == 6 else 'music'
                        expected = [b for b in banks if b['kind'] == kind and b['id'] == handle]
                        self.assertEqual(ref['reference_raw_u16'], handle)
                        self.assertEqual(ref['payload_offset'], 0)
                        self.assertEqual(ref['kind'], kind)
                        self.assertEqual(ref['candidates'], expected)
                        self.assertEqual(ref['status'], 'bank_slot_candidate')
                        for candidate in expected:
                            bank_kind, entry = media[candidate['segment_id'], candidate['id']]
                            self.assertEqual(bank_kind, kind)
                            self.assertEqual(entry['record_sha256'], candidate['record_sha256'])
                            # Independent original name-prefix correlation. No name fields
                            # are interpreted or added to the production annotation.
                            payload = bytes.fromhex(param['payload_hex'])
                            header = bytes.fromhex(entry['header_hex'])
                            self.assertEqual(payload[6:22], header[10:26])
        self.assertEqual(counts, {6: 870, 7: 21})
        self.assertEqual(path.read_bytes(), raw)
