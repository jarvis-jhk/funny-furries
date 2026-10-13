import collections
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import event_dump as events, project_index as project
from test_event_dump import record, row, event_block, global_block, reconstruct_program


SIZES = {9: 34, 16: 26, 18: 36, 21: 34}


def position_payload(kind, reference=0, target=0, tail=b''):
    payload = bytearray(range(SIZES[kind] - 4))
    struct.pack_into('<H', payload, 0, reference)
    if kind in (9, 18):
        struct.pack_into('<H', payload, 24, target)
    return bytes(payload) + tail


def position_program(parameters):
    return row([record('condition', -1, -9, 0, parameters)],
               [record('action', 2, 3, 0, parameters)]) + bytes(2)


def position_project(parameters):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    def objects(name):
        header = bytearray(68)
        header[:len(name)] = name
        header[0x26] = 0x80
        header[0x2A] = 2
        return struct.pack('<I', 1) + header
    program = position_program(parameters)
    frames = []
    for names in [(b'first\n"name"',), (b'second',), (), (b'one', b'two')]:
        frames.append(bytes(0xB8) + b''.join(block(2, objects(name)) for name in names)
                      + block(0x8004, event_block(program)))
    header = bytearray(0x166 + 4 * len(frames))
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, len(frames))
    body = block(3, global_block(program))
    for i, frame in enumerate(frames):
        struct.pack_into('<I', header, 0x166 + 4 * i, len(header) + len(body) + 6)
        body += block(0x8008 if i == len(frames) - 1 else 8, frame)
    return bytes(header) + body, program


class PositionTests(unittest.TestCase):
    def test_all_four_types_in_conditions_actions_frame_and_global_lossless(self):
        for kind in SIZES:
            payload = position_payload(kind, 0x1234, 0x2345, b'\xffopaque\0')
            raw = position_program([(kind, payload)])
            for out in [events.decode_program(event_block(raw)), events.decode_global_program(global_block(raw))]:
                self.assertEqual(reconstruct_program(out), raw)
                for rec in out['rows'][0]['records']:
                    param = rec['parameters'][0]
                    self.assertEqual(bytes.fromhex(param['payload_hex']), payload)
                    self.assertEqual(param['meaning'], 'unknown')
                    refs = param['position_reference_storage']['references']
                    self.assertEqual([r['role'] for r in refs], ['position_reference'] +
                                     (['creation_target'] if kind in (9, 18) else []))
                    self.assertEqual([r['payload_offset'] for r in refs], [0] + ([24] if kind in (9, 18) else []))
                    self.assertEqual([r['reference_raw_u16'] for r in refs], [0x1234] +
                                     ([0x2345] if kind in (9, 18) else []))
                    self.assertTrue(all(r['status'] == 'frame_context_unresolved' and not r['candidates'] for r in refs))

    def test_absolute_sentinels_apply_only_to_position_not_creation_target(self):
        for ref in (0xFFFE, 0xFFFF):
            for kind in SIZES:
                refs = events.decode_position_references(position_payload(kind, ref, ref), kind)['references']
                self.assertEqual(refs[0]['reference_raw_u16'], ref)
                self.assertEqual(refs[0]['status'], 'absolute_position_sentinel')
                self.assertEqual(refs[0]['candidates'], [])
                if len(refs) == 2:
                    self.assertEqual(refs[1]['status'], 'frame_context_unresolved')
        for ref in (0, 0x3FFF, 0x4000, 0xFFFD):
            self.assertEqual(events.decode_position_references(position_payload(16, ref), 16)
                             ['references'][0]['status'], 'frame_context_unresolved')

    def test_truncated_known_shapes_refused_unknown_types_retained(self):
        for kind, size in SIZES.items():
            for length in (0, 1, 2, size - 5):
                with self.subTest(kind=kind, length=length):
                    with self.assertRaises(project.InputError):
                        events.decode_rows(position_program([(kind, bytes(length))]))
        for kind in (0, 8, 10, 17, 19, 20, 999):
            payload = b'own bytes'
            out = events.decode_rows(position_program([(kind, payload)]))[0]['records'][0]['parameters'][0]
            self.assertNotIn('position_reference_storage', out)
            self.assertEqual(out['payload_hex'], payload.hex())


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class PositionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_scopes_ambiguity_untyped_names_global_unknown_and_escaped_text(self):
        raw, program = position_project([(9, position_payload(9)), (18, position_payload(18, 0xFFFF, 0x4000))])
        doc = events.event_document(self.reader, raw)
        statuses = []
        for frame in doc['frames']:
            out = frame['programs'][0]
            self.assertEqual(reconstruct_program(out), program)
            params = out['rows'][0]['records'][0]['parameters']
            refs = params[0]['position_reference_storage']['references']
            statuses.append([r['status'] for r in refs])
            self.assertEqual(params[1]['position_reference_storage']['references'][0]['status'], 'absolute_position_sentinel')
            self.assertEqual(params[1]['position_reference_storage']['references'][1]['status'], 'encoded_reference_unresolved')
        self.assertEqual(statuses, [['local_slot_candidate'] * 2, ['local_slot_candidate'] * 2,
                                    ['missing_local_slot'] * 2, ['ambiguous_local_slot'] * 2])
        refs = [f['programs'][0]['rows'][0]['records'][0]['parameters'][0]['position_reference_storage']['references'][0]
                for f in doc['frames']]
        self.assertEqual([r['candidates'][0]['name'] for r in refs[:2]], ['first\n"name"', 'second'])
        self.assertTrue(refs[0]['candidates'][0]['global'])
        self.assertEqual([c['block_id'] for c in refs[3]['candidates']], [0, 1])
        self.assertEqual(reconstruct_program(doc['global_events'][0]), program)
        for rec in doc['global_events'][0]['rows'][0]['records']:
            for param in rec['parameters']:
                for ref in param['position_reference_storage']['references']:
                    self.assertEqual(ref['status'], 'absolute_position_sentinel' if
                                     ref['role'] == 'position_reference' and ref['reference_raw_u16'] == 0xFFFF
                                     else 'frame_context_unresolved')
                    self.assertEqual(ref['candidates'], [])
        lines = [s for s in events.readable(doc).splitlines() if s.startswith('          POSITION_REFERENCES ')]
        self.assertEqual(len(lines), 20)
        self.assertIn('first\\n\\"name\\"', lines[0])
        self.assertEqual(doc['schema_version'], 15)
        self.assertTrue(doc['coverage']['position_reference_storage'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        self.assertFalse(doc['coverage']['global_reference_resolution'])
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_deleted_slots_and_distinct_creation_target_without_type_guess(self):
        raw, _ = position_project([(9, position_payload(9, 0, 1))])
        # Mark the first local definition deleted; raw parameter decoding remains valid.
        game = self.reader.read(raw)
        level = game.levels()[0]
        block = next(b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2)
        at = level.offset + 6 + block.offset + 6 + 4 + 0x2A
        changed = bytearray(raw)
        changed[at] = 0xFF
        doc = events.event_document(self.reader, bytes(changed))
        refs = doc['frames'][0]['programs'][0]['rows'][0]['records'][0]['parameters'][0]['position_reference_storage']['references']
        self.assertEqual([r['status'] for r in refs], ['deleted_local_slot', 'missing_local_slot'])
        self.assertEqual([r['reference_raw_u16'] for r in refs], [0, 1])

    def test_pinned_remapper_independently_changes_exact_reference_words(self):
        from klikback.core.common import reconstruct_event_test as independent
        self.assertEqual(SIZES, independent.OBJECT_POSITION_PARAMETER_SIZES)
        for kind in SIZES:
            for reference in (7, 0xFFFE, 0xFFFF):
                payload = position_payload(kind, reference, 9, b'own tail')
                parameter = struct.pack('<HH', len(payload) + 4, kind) + payload
                mapped = bytearray(parameter)
                independent.remap_object_position_parameter(mapped, 0, len(mapped), kind,
                                                            {7: 101, 9: 202, 0xFFFE: 303, 0xFFFF: 404})
                refs = events.decode_position_references(payload, kind)['references']
                for ref in refs:
                    at = 4 + ref['payload_offset']
                    self.assertEqual(int.from_bytes(parameter[at:at + 2], 'little'), ref['reference_raw_u16'])
                    expected = reference if ref['status'] == 'absolute_position_sentinel' else (
                        101 if ref['role'] == 'position_reference' else 202)
                    self.assertEqual(int.from_bytes(mapped[at:at + 2], 'little'), expected)
                self.assertEqual(mapped[0x14:0x16], bytes(2))
                self.assertEqual(parameter[4:], payload)

    def test_late_invalid_positions_refuse_json_text_bundle_before_save_or_report(self):
        from tools import export_project
        raw, _ = position_project([(9, position_payload(9))])
        old = record('action', 2, 3, 0, [(9, position_payload(9))])
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        # Preserve every container extent; the final parameter alone becomes too short.
        new = record('action', 2, 3, 0, [(9, position_payload(9)[:-4]), (999, b'')])
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

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_reference_words_external_traversal_candidates_and_lossless_programs(self):
        from klikback.core.common import event_object_registry as independent
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        params, statuses = collections.Counter(), collections.Counter()
        contexts = {}
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            objects = [(i, self.reader.object_definitions(b.data))
                       for i, b in enumerate(self.reader.level_blocks(level.data)[1]) if b.ident == 2]
            for program in frame['programs']:
                contexts[id(program)] = objects
        programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
        for program in programs:
            source = reconstruct_program(program)
            for row_ in program['rows']:
                expected_refs = []
                for rec in row_['records']:
                    for param in rec['parameters']:
                        if param['type'] not in SIZES:
                            self.assertNotIn('position_reference_storage', param)
                            continue
                        params[param['type']] += 1
                        parameter = source[param['offset']:param['offset'] + param['bytes']]
                        self.assertEqual(parameter[4:].hex(), param['payload_hex'])
                        for ref in param['position_reference_storage']['references']:
                            at = 4 if ref['role'] == 'position_reference' else 0x1C
                            self.assertEqual(ref['reference_raw_u16'], int.from_bytes(parameter[at:at + 2], 'little'))
                            self.assertEqual(ref['payload_offset'], at - 4)
                            if ref['status'] != 'absolute_position_sentinel':
                                expected_refs.append((ref['role'].replace('_', ' '), None, ref['reference_raw_u16']))
                            expected_candidates = [
                                {'block_id': block_id, 'id': o.index, 'name': o.name,
                                 'type': o.object_type, 'type_name': o.type_name,
                                 'global': o.is_global, 'deleted': o.deleted}
                                for block_id, objects in contexts.get(id(program), []) for o in objects
                                if o.index == ref['reference_raw_u16'] and o.index < 0x4000]
                            self.assertEqual(ref['candidates'], expected_candidates)
                            statuses[ref['status']] += 1
                row_bytes = source[row_['offset']:row_['offset'] + row_['bytes']]
                actual = [r for r in independent.event_object_slots(row_bytes)
                          if r[0] in ('position reference', 'creation target')]
                self.assertEqual(expected_refs, actual)
        self.assertEqual(params, {9: 1150, 16: 3, 18: 110})
        self.assertEqual(statuses, {'local_slot_candidate': 2520, 'frame_context_unresolved': 3})
        self.assertEqual(sum(statuses.values()), 2523)
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
