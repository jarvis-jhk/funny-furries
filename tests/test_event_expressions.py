import collections
import copy
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import event_dump as events, project_index as project
from test_event_dump import record, row, event_block, global_block, reconstruct_program
from test_event_references import object_entry


def token(code, payload=b''):
    return struct.pack('<HH', code, 4 + len(payload)) + payload


def expression(tokens=(), prefix=0xFEDC, suffix=b''):
    return struct.pack('<H', prefix) + b''.join(tokens) + bytes(2) + suffix


def expression_program(payload, kind=22):
    return row([record('condition', -1, -9, 0, [(kind, payload)])],
               [record('action', 2, 3, 0, [(kind, payload)])]) + bytes(2)


def expression_project(payload):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    def objects(name):
        header = bytearray(68)
        header[:len(name)] = name
        header[0x26] = 0x80
        header[0x2A] = 2
        return struct.pack('<I', 1) + header
    program = expression_program(payload)
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


def reconstruct_expression(out):
    return (struct.pack('<H', out['prefix_raw_u16'])
            + b''.join(bytes.fromhex(t['raw_hex']) for t in out['tokens'])
            + bytes(2) + bytes.fromhex(out['suffix_hex']))


class ExpressionTests(unittest.TestCase):
    def test_order_unknown_codes_opaque_prefix_suffix_and_exact_reconstruction(self):
        items = [token(0x00FF, b'\xff\xff\xff\xff'), token(0x0200),
                 token(0x3021, struct.pack('<HH', 0x3FFF, 0xABCD)),
                 token(0xFFFE, b'own\0bytes'), token(0x0002, struct.pack('<HH', 7, 9))]
        raw = expression(items, suffix=b'\x00\xFF\nopaque')
        out = events.decode_expression(raw)
        self.assertEqual(out['prefix_raw_u16'], 0xFEDC)
        self.assertEqual([t['code_raw_u16'] for t in out['tokens']], [0xFF, 0x200, 0x3021, 0xFFFE, 2])
        offsets = [2]
        for item in items[:-1]:
            offsets.append(offsets[-1] + len(item))
        self.assertEqual([t['payload_offset'] for t in out['tokens']], offsets)
        self.assertEqual(out['terminator_payload_offset'], 2 + sum(map(len, items)))
        self.assertEqual(out['suffix_hex'], b'\x00\xFF\nopaque'.hex())
        self.assertEqual([t['raw_hex'] for t in out['tokens']], [t.hex() for t in items])
        self.assertEqual([t['object_reference_annotation']['expected_type']
                          if t['object_reference_annotation'] else None for t in out['tokens']],
                         [None, None, 33, None, None])
        self.assertEqual(out['tokens'][-1]['object_reference_annotation']['reference_raw_u16'], 7)
        self.assertTrue(all(t['meaning'] == 'unknown' for t in out['tokens']))
        self.assertEqual(reconstruct_expression(out), raw)

    def test_all_six_parameter_types_in_conditions_actions_frame_and_global(self):
        payload = expression([token(0xFF, struct.pack('<i', -123))])
        for kind in [15, 22, 23, 45, 52, 53]:
            raw = expression_program(payload, kind)
            for doc in [events.decode_program(event_block(raw)), events.decode_global_program(global_block(raw))]:
                for rec in doc['rows'][0]['records']:
                    param = rec['parameters'][0]
                    self.assertEqual(reconstruct_expression(param['expression_storage']), payload)
                    self.assertEqual(param['meaning'], 'unknown')
                self.assertEqual(reconstruct_program(doc), raw)
        raw = expression_program(b'not an expression', 999)
        self.assertNotIn('expression_storage', events.decode_rows(raw)[0]['records'][0]['parameters'][0])

    def test_empty_expression_and_first_terminator_retains_arbitrary_tail(self):
        for suffix in [b'', bytes(8), token(0x3002, bytes(4)), b'\xff']:
            raw = expression(suffix=suffix)
            out = events.decode_expression(raw)
            self.assertEqual(out['tokens'], [])
            self.assertEqual(out['terminator_payload_offset'], 2)
            self.assertEqual(reconstruct_expression(out), raw)

    def test_truncated_fields_bad_sizes_short_object_tokens_and_missing_terminators(self):
        bad = [b'', b'\0', bytes(2), bytes(3), bytes(2) + b'\xff\0',
               bytes(2) + struct.pack('<HH', 0xFF, 3),
               bytes(2) + struct.pack('<HH', 0xFF, 65535),
               bytes(2) + token(0xFF, bytes(4)),
               expression([token(2)]), expression([token(0x3021, bytes(3))])]
        for payload in bad:
            with self.subTest(payload=payload.hex()):
                with self.assertRaises(project.InputError):
                    events.decode_rows(expression_program(payload))

    def test_expression_reference_statuses_without_invented_type_or_global_mapping(self):
        cases = [(None, 0, [(2, [object_entry(0, kind=7)])], 'local_slot_candidate'),
                 (2, 0, [(2, [object_entry(0)])], 'local_slot_match'),
                 (2, 0, [(2, [object_entry(0, kind=7)])], 'type_mismatch'),
                 (None, 0, [], 'missing_local_slot'),
                 (None, 0, [(2, [object_entry(0, deleted=True)])], 'deleted_local_slot'),
                 (None, 0, [(2, [object_entry(0)]), (3, [object_entry(0)])], 'ambiguous_local_slot'),
                 (None, 0x4000, [(2, [object_entry(0x4000)])], 'encoded_reference_unresolved'),
                 (2, 0xFFFF, [], 'encoded_reference_unresolved')]
        for kind, ref, lists, status in cases:
            before = copy.deepcopy(lists)
            out = events.reference_annotation({'object_type': kind, 'object_reference': ref}, lists)
            self.assertEqual(out['status'], status)
            self.assertEqual(out['reference_raw_u16'], ref)
            self.assertEqual(lists, before)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ExpressionContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_separate_frames_repeated_missing_lists_global_unresolved_and_readable_escaping(self):
        payload = expression([token(0x0002, bytes(4)), token(0x3002, bytes(4)),
                              token(0x3007, bytes(4)), token(0x3002, struct.pack('<HH', 0x4000, 0))])
        raw, program = expression_project(payload)
        doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 29)
        statuses = []
        for frame in doc['frames']:
            out = frame['programs'][0]
            self.assertEqual(reconstruct_program(out), program)
            targets = out['rows'][0]['records'][0]['parameters'][0]['expression_storage']['tokens']
            statuses.append([t['object_reference_annotation']['status'] for t in targets])
        self.assertEqual(statuses, [
            ['local_slot_candidate', 'local_slot_match', 'type_mismatch', 'encoded_reference_unresolved'],
            ['local_slot_candidate', 'local_slot_match', 'type_mismatch', 'encoded_reference_unresolved'],
            ['missing_local_slot'] * 3 + ['encoded_reference_unresolved'],
            ['ambiguous_local_slot'] * 3 + ['encoded_reference_unresolved']])
        targets = [f['programs'][0]['rows'][0]['records'][0]['parameters'][0]['expression_storage']['tokens'][0]
                   ['object_reference_annotation'] for f in doc['frames']]
        self.assertEqual([t['candidates'][0]['name'] for t in targets[:2]], ['first\n"name"', 'second'])
        self.assertEqual([t['block_id'] for t in targets[3]['candidates']], [0, 1])
        self.assertTrue(targets[0]['candidates'][0]['global'])
        self.assertEqual(reconstruct_program(doc['global_events'][0]), program)
        for rec in doc['global_events'][0]['rows'][0]['records']:
            for t in rec['parameters'][0]['expression_storage']['tokens']:
                self.assertEqual(t['object_reference_annotation']['status'], 'frame_context_unresolved')
                self.assertEqual(t['object_reference_annotation']['candidates'], [])
        text = events.readable(doc)
        lines = [line for line in text.splitlines() if line.startswith('          EXPRESSION ')]
        self.assertEqual(len(lines), 10)
        self.assertIn('first\\n\\"name\\"', lines[0])
        self.assertTrue(doc['coverage']['expression_token_storage'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        self.assertFalse(doc['coverage']['global_reference_resolution'])
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_late_invalid_expression_refuses_json_text_bundle_without_reporting(self):
        from tools import export_project
        raw, _ = expression_project(expression([token(0xFF, bytes(4))]))
        # Equal-size corruption in the last frame's second expression: no earlier
        # valid expression may cause a partially written document/bundle.
        at = raw.rfind(token(0xFF, bytes(4)))
        bad = raw[:at + 2] + struct.pack('<H', 65535) + raw[at + 4:]
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
    def test_original_tokens_source_spans_external_reference_helper_and_lossless_bytes(self):
        from klikback.core.common import event_object_registry as independent
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        params = collections.Counter()
        codes = collections.Counter()
        targets = collections.Counter()
        tails = collections.Counter()
        programs = [p for f in doc['frames'] for p in f['programs']] + doc['global_events']
        contexts = {}
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            objects = [(i, self.reader.object_definitions(b.data))
                       for i, b in enumerate(self.reader.level_blocks(level.data)[1]) if b.ident == 2]
            for program in frame['programs']:
                contexts[id(program)] = objects
        for program in programs:
            source = reconstruct_program(program)
            for row_ in program['rows']:
                for rec in row_['records']:
                    for param in rec['parameters']:
                        if param['type'] not in independent.EXPRESSION_PARAMETERS:
                            self.assertNotIn('expression_storage', param)
                            continue
                        params[param['type']] += 1
                        offset = param['offset']
                        original = source[offset:offset + param['bytes']]
                        out = param['expression_storage']
                        self.assertEqual(reconstruct_expression(out), original[4:])
                        self.assertEqual(out['prefix_raw_u16'], int.from_bytes(original[4:6], 'little'))
                        refs = list(independent.expression_object_slots(original, 0, len(original)))
                        expected_refs = []
                        for t in out['tokens']:
                            start = 4 + t['payload_offset']
                            self.assertEqual(bytes.fromhex(t['raw_hex']), original[start:start + t['bytes']])
                            self.assertEqual(t['code_raw_u16'], int.from_bytes(original[start:start + 2], 'little'))
                            self.assertEqual(t['bytes'], int.from_bytes(original[start + 2:start + 4], 'little'))
                            codes[t['code_raw_u16']] += 1
                            ref = t['object_reference_annotation']
                            if ref is not None:
                                self.assertEqual(ref['reference_raw_u16'], int.from_bytes(original[start + 4:start + 6], 'little'))
                                expected_refs.append(('expression token', ref['expected_type'], ref['reference_raw_u16']))
                                expected_candidates = [
                                    {'block_id': block_id, 'id': o.index, 'name': o.name,
                                     'type': o.object_type, 'type_name': o.type_name,
                                     'global': o.is_global, 'deleted': o.deleted}
                                    for block_id, objects in contexts.get(id(program), []) for o in objects
                                    if o.index == ref['reference_raw_u16'] and o.index < 0x4000]
                                self.assertEqual(ref['candidates'], expected_candidates)
                                targets[ref['status']] += 1
                                if ref['candidates']:
                                    self.assertEqual(ref['candidates'][0]['id'], ref['reference_raw_u16'])
                                    if ref['expected_type'] is not None:
                                        self.assertEqual(ref['candidates'][0]['type'], ref['expected_type'])
                        self.assertEqual(expected_refs, refs)
                        tails[out['suffix_hex']] += 1
        self.assertEqual(params, {22: 2461, 23: 1400, 45: 7})
        self.assertEqual(sum(codes.values()), 4485)
        self.assertEqual(len(codes), 22)
        self.assertEqual(tails, {'': 3686, '00' * 8: 173, '00' * 4: 9})
        self.assertEqual(targets, {'local_slot_match': 17, 'local_slot_candidate': 81,
                                  'frame_context_unresolved': 190})
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
