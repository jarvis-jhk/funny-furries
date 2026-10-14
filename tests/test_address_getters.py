import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project as bundle, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import expression_program, expression_project

HEADER_TYPES = {6, 7, 8, 9, 11, 13, 18, 19, 20, 21, 25, 27, 28, 30, 31, 33, 35, 36, 37, 38, 39, 41, 43, 44, 47, 48, 49}
PAYLOAD_TYPES = {40}
ORIGINAL_COUNTS = {6: 870, 7: 21, 9: 1150, 13: 122, 18: 110, 19: 29, 38: 41, 39: 159, 48: 20}
LATE_HEADER_TYPES = {41, 43, 44, 47, 48, 49}


class AddressGetterTests(unittest.TestCase):
    def test_late_header_entries_accept_empty_payload_without_borrowing_expression_layout(self):
        for kind in LATE_HEADER_TYPES:
            for payload in (b'', b'\xff', b'no terminator', bytes(range(256))):
                source = expression_program(payload, kind)
                rows = events.decode_rows(source)
                self.assertEqual(reconstruct_program({'rows': rows}), source)
                for rec in rows[0]['records']:
                    q = rec['parameters'][0]
                    ret = q['address_getter_storage']['conditional_getter_return']
                    self.assertEqual((ret['parameter_relative_offset'], ret['target']), (0, 'parameter_header'))
                    self.assertEqual((ret['bx_raw_u16'], ret['carry']), (0, False))
                    self.assertEqual(ret['dx'], 'preserved_incoming_word_not_a_new_value_tag')
                    self.assertEqual(q['payload_hex'], payload.hex())
                    self.assertEqual(q['meaning'], 'unknown')
                    self.assertNotIn('expression_storage', q)
                    self.assertNotIn('scalar_getter_storage', q)
                    self.assertNotIn('object_parameter_reference', q)

    def test_exact_header_types_address_not_stored_value_or_payload_pointer(self):
        self.assertEqual(events.ADDRESS_HEADER_TYPES, HEADER_TYPES)
        for kind in HEADER_TYPES:
            for payload in (b'', b'\xff', b'\xfe\xff\x00\x80', bytes(range(256)), b'no NUL terminator'):
                out = events.decode_address_getter(payload, kind)
                ret = out['conditional_getter_return']
                self.assertEqual((ret['parameter_relative_offset'], ret['target']), (0, 'parameter_header'))
                self.assertEqual(out['stored_bytes_from_target'], 4 + len(payload))
                self.assertEqual(ret['eax'], 'runtime_parameter_address_unknown')
                self.assertNotIn('eax_raw_u32', ret)
                self.assertFalse(out['payload_dereferenced_by_getter'])
                self.assertFalse(out['runtime_resolution'])
                self.assertEqual(out['caller_interpretation'], 'unknown')

    def test_type40_payload_address_with_empty_or_arbitrary_unterminated_storage(self):
        self.assertEqual(events.ADDRESS_PAYLOAD_TYPES, PAYLOAD_TYPES)
        for payload in (b'', b'\xff', b'\xff\xff\xff\xff', b'no NUL', bytes(range(256))):
            out = events.decode_address_getter(payload, 40)
            ret = out['conditional_getter_return']
            self.assertEqual((ret['parameter_relative_offset'], ret['target']), (4, 'parameter_payload'))
            self.assertEqual(out['stored_bytes_from_target'], len(payload))
            self.assertEqual((ret['address_arithmetic_bits'], ret['address_overflow']), (32, 'wrap_modulo_2_to_32'))
            self.assertEqual((ret['bx_raw_u16'], ret['carry']), (0, False))
            self.assertEqual(ret['dx'], 'preserved_incoming_word_not_a_new_value_tag')
            self.assertFalse(out['payload_dereferenced_by_getter'])
            self.assertFalse(out['runtime_resolution'])
            rows = events.decode_rows(expression_program(payload, 40))
            for rec in rows[0]['records']:
                self.assertEqual(rec['parameters'][0]['address_getter_storage'], out)
            self.assertEqual(reconstruct_program({'rows': rows}), expression_program(payload, 40))

    def test_other_types_rejected_including_state_dependent_type1(self):
        for kind in range(65536):
            if kind not in HEADER_TYPES | PAYLOAD_TYPES:
                with self.assertRaises(project.InputError):
                    events.decode_address_getter(bytes(40), kind)
        self.assertNotIn(1, events.ADDRESS_HEADER_TYPES)
        self.assertNotIn(16, events.ADDRESS_HEADER_TYPES)

    def test_both_roles_raw_reconstruction_and_prior_audio_position_group_views(self):
        payload = bytes.fromhex('ffff34127856') + bytes(34)
        for kind in range(56):
            # Expression types need valid token streams; they are not address getters.
            if kind in events.EXPRESSION_TYPES:
                continue
            program = expression_program(payload, kind)
            rows = events.decode_rows(program)
            self.assertEqual(reconstruct_program({'rows': rows}), program)
            for rec in rows[0]['records']:
                q = rec['parameters'][0]
                self.assertEqual('address_getter_storage' in q, kind in HEADER_TYPES | PAYLOAD_TYPES)
                self.assertEqual(q['payload_hex'], payload.hex())
                self.assertEqual(q['meaning'], 'unknown')
                if kind in (6, 7):
                    self.assertEqual(q['audio_reference_storage']['reference_raw_u16'], 65535)
                if kind in (9, 18, 21):
                    self.assertIn('position_coordinate_storage', q)
                if kind == 39:
                    self.assertEqual(q['group_parameter_storage']['runtime_raw_u32'], 0x1234FFFF)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class AddressGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def make_project(self, kind=40, payload=b'\xffunterminated'):
        raw, _ = expression_project(payload)
        return raw.replace(struct.pack('<HH', 4 + len(payload), 22), struct.pack('<HH', 4 + len(payload), kind))

    def test_late_header_entries_all_roles_scopes_and_readable_output(self):
        for kind in LATE_HEADER_TYPES:
            raw = self.make_project(kind, b'')
            doc = events.event_document(self.reader, raw)
            count = 0
            for pr in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                self.assertEqual(reconstruct_program(pr), expression_program(b'', kind))
                for rec in pr['rows'][0]['records']:
                    q = rec['parameters'][0]
                    getter = q['address_getter_storage']
                    self.assertEqual(getter['stored_bytes_from_target'], 4)
                    self.assertEqual(getter['conditional_getter_return']['parameter_relative_offset'], 0)
                    self.assertFalse(getter['payload_dereferenced_by_getter'])
                    self.assertFalse(getter['runtime_resolution'])
                    count += 1
            self.assertEqual(count, 10)
            self.assertEqual(events.readable(doc).count('ADDRESS_GETTER '), 10)
            for key in ('parameter_semantics', 'opcode_semantics', 'global_reference_resolution'):
                self.assertFalse(doc['coverage'][key])

    def test_late_type48_malformed_header_refused_before_all_output_or_reporting(self):
        raw = self.make_project(48, b'\xfe\xff')
        at = raw.rfind(struct.pack('<HH', 6, 48))
        self.assertGreater(at, 0)
        bad = raw[:at] + struct.pack('<H', 3) + raw[at + 2:]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as savebundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called(); savebundle.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_type48_raw_words_roles_scopes_and_opaque_caller(self):
        path = Path(os.environ['FF_TEST_PROJECT']); raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        programs = []
        for frame, level in zip(doc['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((pr, blocks[pr['block_id']].data, 'frame') for pr in frame['programs'])
        programs.extend((pr, game.segments[pr['segment_id']].data, 'global') for pr in doc['global_events'])
        from collections import Counter
        roles, scopes, words = Counter(), Counter(), Counter()
        for pr, block, scope in programs:
            data = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), data)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] not in LATE_HEADER_TYPES:
                            continue
                        self.assertEqual(q['type'], 48)
                        at = q['offset']
                        self.assertEqual(struct.unpack_from('<HH', data, at), (12, 48))
                        payload = data[at + 4:at + 12]
                        self.assertEqual(q['payload_hex'], payload.hex())
                        getter = q['address_getter_storage']
                        self.assertEqual(getter['conditional_getter_return']['parameter_relative_offset'], 0)
                        self.assertEqual(getter['stored_bytes_from_target'], 12)
                        self.assertEqual(getter['caller_interpretation'], 'unknown')
                        self.assertFalse(getter['runtime_resolution'])
                        self.assertNotIn('eax_raw_u32', getter['conditional_getter_return'])
                        roles[rec['role']] += 1; scopes[scope] += 1
                        words[struct.unpack('<4H', payload)] += 1
        self.assertEqual(sum(roles.values()), 20)
        self.assertEqual(dict(roles), {'condition': 6, 'action': 14})
        self.assertEqual(dict(scopes), {'frame': 2, 'global': 18})
        self.assertEqual(dict(words), {(1009, 0, 0, 0): 1, (2040, 0, 0, 0): 3,
                                       (2002, 0, 0, 0): 3, (2031, 0, 0, 0): 5,
                                       (2032, 0, 0, 0): 5, (2042, 0, 0, 0): 3})
        self.assertEqual(path.read_bytes(), raw)

    def test_frame_global_both_roles_text_and_no_runtime_content_semantics(self):
        raw = self.make_project()
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['parameter_address_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'expression_evaluation'):
            self.assertFalse(d['coverage'][key])
        for pr in [pr for f in d['frames'] for pr in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), expression_program(b'\xffunterminated', 40))
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                ret = q['address_getter_storage']['conditional_getter_return']
                self.assertEqual(ret['parameter_relative_offset'], 4)
                self.assertFalse(q['address_getter_storage']['runtime_resolution'])
        self.assertEqual(events.readable(d).count('ADDRESS_GETTER '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw = self.make_project(48, b'\xff\xffopaque')
        d = events.event_document(self.reader, raw)
        manifest, files = bundle.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], bundle.json_bytes(d))
        self.assertEqual(files['events.txt'], events.readable(d).encode())
        self.assertFalse(manifest['coverage']['behaviour'])
        with tempfile.TemporaryDirectory() as scratch:
            target = bundle.save_bundle(manifest, files, Path(scratch))
            old = {p.name: p.read_bytes() for p in target.iterdir()}
            bundle.save_bundle(*bundle.research_bundle(self.reader, raw), Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)
            changed = copy.deepcopy(files)
            changed['events.txt'] += b'changed'
            newmanifest = json.loads(changed['manifest.json'])
            for component in newmanifest['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(newmanifest)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(newmanifest, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_broken_parameter_header_refused_before_output_or_reporting(self):
        raw = self.make_project(40, b'\xfe\xff')
        at = raw.rfind(struct.pack('<HH', 6, 40))
        bad = raw[:at] + struct.pack('<H', 3) + raw[at + 2:]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(bundle, 'save_bundle') as savebundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called()
                savebundle.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_independent_source_headers_type_counts_and_reconstruction(self):
        from collections import Counter
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw)
        game = self.reader.read(raw)
        programs = []
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            programs.extend((p, blocks[p['block_id']].data) for p in f['programs'])
        programs.extend((p, game.segments[p['segment_id']].data) for p in d['global_events'])
        counts = Counter()
        for pr, block in programs:
            data = block[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]
            self.assertEqual(reconstruct_program(pr), data)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        at = q['offset']
                        kind = int.from_bytes(data[at + 2:at + 4], 'little')
                        self.assertEqual(kind, q['type'])
                        self.assertEqual(data[at + 4:at + q['bytes']].hex(), q['payload_hex'])
                        if kind not in HEADER_TYPES | PAYLOAD_TYPES:
                            self.assertNotIn('address_getter_storage', q)
                            continue
                        size = int.from_bytes(data[at:at + 2], 'little')
                        offset = 4 if kind == 40 else 0
                        s = q['address_getter_storage']
                        self.assertEqual(s['conditional_getter_return']['parameter_relative_offset'], offset)
                        self.assertEqual(s['stored_bytes_from_target'], size - offset)
                        self.assertFalse(s['runtime_resolution'])
                        counts[kind] += 1
        self.assertEqual(dict(counts), ORIGINAL_COUNTS)
