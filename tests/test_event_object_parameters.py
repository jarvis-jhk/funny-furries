import collections
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import event_dump as events, project_index as project, export_project
from test_event_dump import record, row, event_block, global_block, reconstruct_program
from test_event_positions import position_project
from test_event_references import object_entry


def payload(reference=0, tail=b''):
    return struct.pack('<HHH', 0xABCD, reference, 0xFEDC) + tail


def program(parameters):
    return row([record('condition', -1, -9, 0, parameters)],
               [record('action', 2, 3, 0, parameters)]) + bytes(2)


class ObjectParameterTests(unittest.TestCase):
    def test_word_offset_boundaries_roles_and_opaque_tails(self):
        for ref in (0, 7, 0x3FFF, 0x4000, 0x8000, 0xFFFE, 0xFFFF):
            value = payload(ref, b'\xffown\0tail')
            source = program([(1, value), (999, value)])
            for out in (events.decode_program(event_block(source)),
                        events.decode_global_program(global_block(source))):
                self.assertEqual(reconstruct_program(out), source)
                for rec in out['rows'][0]['records']:
                    a, b = rec['parameters']
                    self.assertEqual(a['payload_hex'], value.hex())
                    self.assertEqual(a['meaning'], 'unknown')
                    self.assertEqual(a['object_parameter_reference'], {
                        'payload_offset': 2, 'reference_raw_u16': ref,
                        'status': 'frame_context_unresolved', 'candidates': []})
                    self.assertNotIn('object_parameter_reference', b)

    def test_short_shapes_refused_and_no_adjacent_word_type_guess(self):
        for length in range(6):
            with self.assertRaises(project.InputError):
                events.decode_rows(program([(1, bytes(length))]))
        out = events.decode_object_parameter(payload(7))
        # Neither unknown neighbour becomes an expected type.
        self.assertNotIn('expected_type', out)
        for kind in (1, 2, 32):
            match = events.reference_annotation({'object_type': None, 'object_reference': 7},
                                               [(3, [object_entry(7, kind=kind)])])
            self.assertEqual(match['status'], 'local_slot_candidate')


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class ObjectParameterContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_frame_context_missing_ambiguous_global_unresolved_and_escaped_text(self):
        raw, source = position_project([(1, payload())])
        doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 13)
        self.assertTrue(doc['coverage']['object_parameter_reference_candidates'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        self.assertFalse(doc['coverage']['global_reference_resolution'])
        statuses = []
        for frame in doc['frames']:
            p = frame['programs'][0]
            self.assertEqual(reconstruct_program(p), source)
            refs = [r['parameters'][0]['object_parameter_reference'] for r in p['rows'][0]['records']]
            self.assertEqual(refs[0], refs[1])
            statuses.append(refs[0]['status'])
        self.assertEqual(statuses, ['local_slot_candidate', 'local_slot_candidate',
                                    'missing_local_slot', 'ambiguous_local_slot'])
        refs = doc['frames'][3]['programs'][0]['rows'][0]['records'][0]['parameters'][0]['object_parameter_reference']
        self.assertEqual([c['block_id'] for c in refs['candidates']], [0, 1])
        for rec in doc['global_events'][0]['rows'][0]['records']:
            self.assertEqual(rec['parameters'][0]['object_parameter_reference']['status'], 'frame_context_unresolved')
            self.assertEqual(rec['parameters'][0]['object_parameter_reference']['candidates'], [])
        lines = [s for s in events.readable(doc).splitlines() if s.startswith('          OBJECT_PARAMETER_REFERENCE ')]
        self.assertEqual(len(lines), 10)
        self.assertIn('first\\n\\"name\\"', lines[0])
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_deleted_and_encoded_slots_have_no_invented_sentinel(self):
        raw, _ = position_project([(1, payload()), (1, payload(0xFFFF))])
        level = self.reader.read(raw).levels()[0]
        b = next(b for b in self.reader.level_blocks(level.data)[1] if b.ident == 2)
        at = level.offset + 6 + b.offset + 6 + 4 + 0x2A
        changed = bytearray(raw)
        changed[at] = 0xFF
        doc = events.event_document(self.reader, bytes(changed))
        refs = [p['object_parameter_reference'] for p in doc['frames'][0]['programs'][0]['rows'][0]['records'][0]['parameters']]
        self.assertEqual([r['status'] for r in refs], ['deleted_local_slot', 'encoded_reference_unresolved'])
        self.assertEqual(refs[1]['candidates'], [])

    def test_external_registry_and_remapper_identify_exact_word_for_both_roles(self):
        from klikback.core.common import event_object_registry as registry, reconstruct_event_test as converter
        source = program([(1, payload(7, b'own tail'))])[:-2]
        found = [r for r in registry.event_object_slots(source) if r[0] == 'object parameter']
        self.assertEqual(found, [('object parameter', None, 7)] * 2)
        mapped = converter.compiled_event_to_editor_event(source, object_id_map={7: 101})
        p = events.decode_rows(source + bytes(2))[0]
        new = events.decode_rows(mapped + bytes(2))[0]
        for old_rec, new_rec in zip(p['records'], new['records']):
            old_param, new_param = old_rec['parameters'][0], new_rec['parameters'][0]
            self.assertEqual(old_param['object_parameter_reference']['reference_raw_u16'], 7)
            self.assertEqual(new_param['object_parameter_reference']['reference_raw_u16'], 101)
            expected = bytearray.fromhex(old_param['payload_hex'])
            expected[2:4] = struct.pack('<H', 101)
            self.assertEqual(new_param['payload_hex'], expected.hex())

    def test_late_invalid_parameter_refused_before_write_or_report(self):
        raw, _ = position_project([(1, payload())])
        old = record('action', 2, 3, 0, [(1, payload())])
        at = raw.rfind(old)
        self.assertGreater(at, 0)
        new = record('action', 2, 3, 0, [(1, payload()[:2]), (999, b'')])
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

    def test_bundle_contains_same_object_annotations_and_repeats(self):
        raw, _ = position_project([(1, payload())])
        manifest, files = export_project.research_bundle(self.reader, raw)
        self.assertEqual(files['events.json'], export_project.json_bytes(events.event_document(self.reader, raw)))
        self.assertIn(b'OBJECT_PARAMETER_REFERENCE', files['events.txt'])
        self.assertEqual(manifest['components']['events.json'], {'exporter': 'event-dump/13', 'schema_version': 13})
        self.assertEqual(export_project.research_bundle(self.reader, raw), (manifest, files))

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_source_words_registry_candidates_and_reconstruction(self):
        from klikback.core.common import event_object_registry as registry
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        contexts = {}
        for frame, level in zip(doc['frames'], self.reader.read(raw).levels()):
            objects = [(i, self.reader.object_definitions(b.data)) for i, b in
                       enumerate(self.reader.level_blocks(level.data)[1]) if b.ident == 2]
            for p in frame['programs']:
                contexts[id(p)] = objects
        counts = collections.Counter()
        for p in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
            source = reconstruct_program(p)
            for r in p['rows']:
                expected = []
                for rec in r['records']:
                    for param in rec['parameters']:
                        if param['type'] != 1:
                            self.assertNotIn('object_parameter_reference', param)
                            continue
                        out = param['object_parameter_reference']
                        at = param['offset'] + 6
                        ref = int.from_bytes(source[at:at + 2], 'little')
                        self.assertEqual(out['reference_raw_u16'], ref)
                        self.assertEqual(out['payload_offset'], 2)
                        expected.append(('object parameter', None, ref))
                        candidates = [{'block_id': i, 'id': o.index, 'name': o.name,
                                       'type': o.object_type, 'type_name': o.type_name,
                                       'global': o.is_global, 'deleted': o.deleted}
                                      for i, objects in contexts.get(id(p), []) for o in objects
                                      if o.index == ref and ref < 0x4000]
                        self.assertEqual(out['candidates'], candidates)
                        counts[out['status']] += 1
                row_bytes = source[r['offset']:r['offset'] + r['bytes']]
                self.assertEqual(expected, [x for x in registry.event_object_slots(row_bytes) if x[0] == 'object parameter'])
        self.assertEqual(counts, {'local_slot_candidate': 760, 'frame_context_unresolved': 214})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(events.event_document(self.reader, raw), doc)
        print('Original object parameter statuses:', dict(counts))


if __name__ == '__main__':
    unittest.main()
