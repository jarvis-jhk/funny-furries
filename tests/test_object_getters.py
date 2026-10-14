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
from test_event_dump import record, reconstruct_program
from test_event_object_parameters import program
from test_event_positions import position_project


def payload(first=0x1234, second=7, tail=b''):
    return struct.pack('<HHH', first, second, 0xFEDC) + tail


class ObjectGetterTests(unittest.TestCase):
    def test_every_first_word_is_separate_from_editor_reference_and_live_gate(self):
        for first in range(65536):
            out = events.decode_object_getter(payload(first))
            self.assertEqual(out['selection_input_payload_offset'], 0)
            self.assertEqual(out['selection_input_raw_u16'], first)
            self.assertEqual(out['selected_branch'], 'requires_live_runtime_gate')
            self.assertEqual(out['runtime_gate_byte'], 'unknown')
            self.assertIsNone(out['resolved_eax'])
            self.assertFalse(out['runtime_resolution'])
            self.assertEqual(events.decode_object_parameter(payload(first))['reference_raw_u16'], 7)

    def test_inactive_header_and_active_helper_carry_branches_do_not_infer_pointer(self):
        out = events.decode_object_getter(payload())
        inactive = out['conditional_inactive_return']
        self.assertEqual(inactive['eax'], 'runtime_parameter_header_address_unknown')
        self.assertEqual((inactive['parameter_relative_offset'], inactive['bx_raw_u16'], inactive['carry']), (0, 0, False))
        self.assertFalse(inactive['payload_dereferenced_by_getter'])
        self.assertEqual(inactive['dx'], 'preserved_incoming_word_not_a_new_value_tag')
        active = out['conditional_active_normal_return']
        self.assertEqual(active['eax'], 'selection_helper_return_esi')
        self.assertEqual(active['helper_carry_set'], {'bx_raw_u16': 0, 'carry': False})
        self.assertEqual(active['helper_carry_clear'], {'bx': 'selection_helper_return_bx', 'carry': True})
        self.assertEqual(active['dx'], 'selection_helper_return_word_not_a_new_expression_tag')
        self.assertEqual(active['returned_pointer_validity'], 'unknown')
        self.assertEqual(active['selection_helper_side_effects'], 'live_state_dependent')
        self.assertEqual(out['caller_interpretation'], 'unknown')

    def test_exact_type_both_roles_opaque_words_and_raw_reconstruction(self):
        for first, second in ((0, 65535), (65535, 0), (32768, 7), (7, 32768)):
            data = payload(first, second, b'\xffopaque\0tail')
            source = program([(1, data), (999, data)])
            rows = events.decode_rows(source)
            self.assertEqual(reconstruct_program({'rows': rows}), source)
            for rec in rows[0]['records']:
                q, other = rec['parameters']
                self.assertEqual(q['object_getter_storage']['selection_input_raw_u16'], first)
                self.assertEqual(q['object_parameter_reference']['reference_raw_u16'], second)
                self.assertEqual(q['payload_hex'], data.hex())
                self.assertEqual(q['meaning'], 'unknown')
                self.assertNotIn('object_getter_storage', other)

    def test_short_type1_refused_despite_conditional_header_only_branch(self):
        for n in range(6):
            with self.assertRaises(project.InputError):
                events.decode_object_getter(bytes(n))
            with self.assertRaises(project.InputError):
                events.decode_rows(program([(1, bytes(n))]))


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ObjectGetterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_scopes_roles_preserve_candidates_and_false_semantic_coverage(self):
        raw, source = position_project([(1, payload(0x8001, 0))])
        d = events.event_document(self.reader, raw)
        self.assertTrue(d['coverage']['type1_object_getter_inputs'])
        for key in ('parameter_semantics', 'opcode_semantics', 'global_reference_resolution'):
            self.assertFalse(d['coverage'][key])
        statuses = []
        for pr in [p for f in d['frames'] for p in f['programs']] + d['global_events']:
            self.assertEqual(reconstruct_program(pr), source)
            for rec in pr['rows'][0]['records']:
                q = rec['parameters'][0]
                self.assertEqual(q['object_getter_storage']['selection_input_raw_u16'], 0x8001)
                self.assertEqual(q['object_parameter_reference']['reference_raw_u16'], 0)
                statuses.append(q['object_parameter_reference']['status'])
                self.assertIsNone(q['object_getter_storage']['resolved_eax'])
        self.assertEqual(statuses, ['local_slot_candidate'] * 4 + ['missing_local_slot'] * 2 + ['ambiguous_local_slot'] * 2 + ['frame_context_unresolved'] * 2)
        self.assertEqual(events.readable(d).count('OBJECT_GETTER '), 10)
        self.assertEqual(events.event_document(self.reader, raw), d)

    def test_bundle_standalone_agreement_repeat_and_immutable_refusal(self):
        raw, _ = position_project([(1, payload())])
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
            updated = json.loads(changed['manifest.json'])
            for component in updated['files']:
                if component['file'] == 'events.txt':
                    component['bytes'] = len(changed['events.txt'])
                    component['sha256'] = hashlib.sha256(changed['events.txt']).hexdigest()
            changed['manifest.json'] = bundle.json_bytes(updated)
            with self.assertRaises(project.InputError):
                bundle.save_bundle(updated, changed, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, old)

    def test_late_short_object_refused_before_output_or_reporting(self):
        raw, _ = position_project([(1, payload())])
        old = record('action', 2, 3, 0, [(1, payload())])
        new = record('action', 2, 3, 0, [(1, payload()[:2]), (999, b'')])
        self.assertEqual(len(old), len(new))
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        bad = raw[:at] + new + raw[at + len(old):]
        for module, flags in [(events, []), (events, ['--text']), (bundle, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=bad), \
                    patch.object(project, 'save_export') as write, \
                    patch.object(bundle, 'save_bundle') as save, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                write.assert_not_called(); save.assert_not_called(); report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_source_words_and_unresolved_gate_candidates(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        d = events.event_document(self.reader, raw)
        programs = []
        game = self.reader.read(raw)
        for f, level in zip(d['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for pr in f['programs']:
                programs.append((pr, blocks[pr['block_id']].data[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]))
        for pr in d['global_events']:
            data = game.segments[pr['segment_id']].data
            programs.append((pr, data[pr['program_offset']:pr['program_offset'] + pr['program_bytes']]))
        counts = {}
        different = 0
        for pr, original in programs:
            self.assertEqual(reconstruct_program(pr), original)
            for row in pr['rows']:
                for rec in row['records']:
                    for q in rec['parameters']:
                        if q['type'] != 1:
                            self.assertNotIn('object_getter_storage', q)
                            continue
                        at = q['offset'] + 4
                        data = original[at:at + q['bytes'] - 4]
                        first, second = struct.unpack_from('<HH', data)
                        self.assertEqual(bytes.fromhex(q['payload_hex']), data)
                        g = q['object_getter_storage']
                        self.assertEqual(g['selection_input_raw_u16'], first)
                        self.assertEqual(q['object_parameter_reference']['reference_raw_u16'], second)
                        self.assertFalse(g['runtime_resolution'])
                        self.assertIsNone(g['resolved_eax'])
                        self.assertEqual(g['runtime_gate_byte'], 'unknown')
                        counts[rec['role']] = counts.get(rec['role'], 0) + 1
                        different += first != second
        self.assertEqual(counts, {'condition': 690, 'action': 284})
        self.assertEqual(different, 974)
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
