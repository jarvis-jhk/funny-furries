import collections
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events
from tools import project_index as project
from test_event_dump import global_block, sample_program, reconstruct_program
from test_project_index import synthetic_project


def project_globals(reader, payloads):
    base = bytearray(synthetic_project())
    last = reader.read(base).segments[-1].offset
    struct.pack_into('<H', base, last, reader.read(base).segments[-1].ident)
    for i, payload in enumerate(payloads):
        base += struct.pack('<HI', 3 | (0x8000 if i == len(payloads) - 1 else 0), len(payload))
        base += payload
    return bytes(base)


class GlobalStructureTests(unittest.TestCase):
    def test_order_offsets_unknown_header_and_lossless_regions(self):
        raw = global_block(sample_program(), b'\xff\x00editor\x80')
        doc = events.decode_global_program(raw)
        self.assertEqual(reconstruct_program(doc), sample_program())
        self.assertEqual(doc['header_hex'], raw[:40].hex())
        self.assertEqual(doc['program_offset'], 49)
        self.assertEqual(doc['program_bytes'], len(sample_program()))
        self.assertEqual(doc['auxiliary'], [{'id': 0, 'offset': 40, 'bytes': 9,
                                           'meaning': 'unknown', 'raw_hex': raw[40:49].hex()}])
        self.assertEqual(bytes.fromhex(doc['header_hex']) + bytes.fromhex(
            doc['auxiliary'][0]['raw_hex']) + reconstruct_program(doc), raw)
        self.assertEqual([r['id'] for r in doc['rows']], [0, 1])
        parameter = doc['rows'][0]['records'][0]['parameters'][0]
        self.assertEqual(parameter['offset'], 28)
        self.assertEqual(parameter['payload_hex'], b'own-test-data'.hex())
        self.assertEqual(parameter['meaning'], 'unknown')

    def test_empty_program_and_empty_opaque_region(self):
        for auxiliary in (b'', b'\xff\x80'):
            with self.subTest(auxiliary=auxiliary):
                raw = global_block(bytes(2), auxiliary)
                doc = events.decode_global_program(raw)
                self.assertEqual(doc['rows'], [])
                self.assertEqual(doc['program_offset'], 40 + len(auxiliary))
                self.assertEqual(doc['program_bytes'], 2)
                self.assertEqual(doc['auxiliary'][0]['bytes'], len(auxiliary))
                self.assertEqual(reconstruct_program(doc), bytes(2))

    def test_header_total_start_size_and_unsupported_extent_fail(self):
        raw = global_block(sample_program())
        bad = [raw[:n] for n in (0, 1, 23, 39, 40, len(raw) - 1)] + [raw + b'x']
        for at, value in [(0, 0), (0, len(raw) - 1), (0, len(raw) + 1),
                          (8, 24), (8, 41), (8, 0xFFFFFFFF),
                          (12, 0), (12, 39), (12, len(raw)), (12, 0xFFFFFFFF),
                          (16, 0), (16, 1), (16, 0xFFFFFFFF)]:
            changed = bytearray(raw)
            struct.pack_into('<I', changed, at, value)
            bad.append(changed)
        for changed in bad:
            with self.subTest(data=changed[:24]), self.assertRaises(project.InputError):
                events.decode_global_program(changed)

    def test_invalid_rows_parameters_counts_and_terminators_fail(self):
        program = sample_program()
        bad = [program[:-2], program + b'extra', b'', b'\0', b'\0\0x']
        for at, form, value in [(0, '<h', -13), (2, '<B', 0), (3, '<B', 10),
                                (14, '<H', 65535), (24, '<B', 0), (28, '<H', 3)]:
            changed = bytearray(program)
            struct.pack_into(form, changed, at, value)
            bad.append(changed)
        for changed in bad:
            with self.subTest(data=changed[:16]), self.assertRaises(project.InputError):
                events.decode_global_program(global_block(changed))

    def test_readable_global_rows_parameters_unknowns_and_empty_region(self):
        doc = events.decode_global_program(global_block(sample_program(), b''))
        text = events.readable({'source': {'sha256': 'a' * 64}, 'frames': [],
                                'global_events': [{'segment_id': 7, 'offset': 900,
                                                   'bytes': 40 + len(sample_program()), **doc}]})
        self.assertIn('GLOBAL SEGMENT 7 offset=900', text)
        self.assertIn('program_offset=40', text)
        self.assertLess(text.index('ROW 0'), text.index('ROW 1'))
        self.assertLess(text.index('CONDITION 0'), text.index('ACTION 1'))
        self.assertIn('type=999 meaning=UNKNOWN payload=' + b'own-test-data'.hex(), text)
        self.assertIn('AUX 0 offset=40 bytes=0 meaning=UNKNOWN raw=', text)
        self.assertEqual(text.count('TERMINATOR 0000'), 1)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class GlobalContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_missing_empty_and_repeated_global_segments_retain_identity(self):
        missing = events.event_document(self.reader, synthetic_project())
        self.assertEqual(missing['global_events'], [])
        payloads = [global_block(sample_program()), global_block(bytes(2), b'')]
        raw = project_globals(self.reader, payloads)
        doc = events.event_document(self.reader, raw)
        self.assertEqual(doc['schema_version'], 32)
        self.assertEqual(doc['exporter'], 'event-dump/32')
        segments = [(i, s) for i, s in enumerate(self.reader.read(raw).segments) if s.ident == 3]
        self.assertEqual(len(doc['global_events']), 2)
        for out, (i, source), payload in zip(doc['global_events'], segments, payloads):
            self.assertEqual((out['segment_id'], out['offset']), (i, source.offset))
            self.assertEqual(out['raw_hex'], payload.hex())
            self.assertEqual(out['sha256'], hashlib.sha256(payload).hexdigest())
            self.assertEqual(out['bytes'], len(payload))
        self.assertEqual(reconstruct_program(doc['global_events'][0]), sample_program())
        self.assertEqual(doc['global_events'][1]['rows'], [])
        self.assertEqual(doc['frames'], [{'id': 0, 'programs': []}])
        self.assertTrue(doc['coverage']['global_event_structure'])
        self.assertFalse(doc['coverage']['opcode_semantics'])
        self.assertFalse(doc['coverage']['parameter_semantics'])
        self.assertEqual(events.event_document(self.reader, raw), doc)

    def test_invalid_later_global_fails_before_either_output_or_report(self):
        for text in (False, True):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'synthetic.cca'
                path.write_bytes(project_globals(self.reader, [global_block(sample_program()), b'bad']))
                argv = ['events', str(path), '--klikback-src', os.environ['FF_KLIKBACK_SRC']]
                if text:
                    argv.append('--text')
                with patch.object(events.sys, 'argv', argv), patch.object(project, 'save_export') as save, \
                        patch.object(project, 'report_fault') as report:
                    self.assertEqual(events.main(), 2)
                save.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_global_source_extents_external_rows_and_reconstruction(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        doc = events.event_document(self.reader, raw)
        sources = [(i, s) for i, s in enumerate(self.reader.read(raw).segments) if s.ident == 3]
        self.assertEqual(len(sources), 1)
        counts = collections.Counter()
        for out, (i, segment) in zip(doc['global_events'], sources):
            data = segment.data
            # Read the source words independently and rebuild from component
            # storage rather than accepting the redundant whole-payload copy.
            total, header_size, start, size = [int.from_bytes(data[p:p + 4], 'little')
                                              for p in (0, 8, 12, 16)]
            self.assertEqual((total, header_size, start, size), (63602, 40, 9916, 53686))
            self.assertEqual((out['segment_id'], out['offset']), (i, segment.offset))
            self.assertEqual((out['program_offset'], out['program_bytes']), (start, size))
            self.assertEqual(bytes.fromhex(out['header_hex']), data[:header_size])
            self.assertEqual(bytes.fromhex(out['auxiliary'][0]['raw_hex']), data[header_size:start])
            program = reconstruct_program(out)
            self.assertEqual(program, data[start:start + size])
            self.assertEqual([(r['offset'], r['bytes']) for r in out['rows']],
                             self.reader.event_groups(data[start:start + size]))
            self.assertEqual(bytes.fromhex(out['header_hex']) + bytes.fromhex(
                out['auxiliary'][0]['raw_hex']) + program, data)
            self.assertEqual(out['raw_hex'], data.hex())
            self.assertEqual(out['sha256'], hashlib.sha256(data).hexdigest())
            for row in out['rows']:
                counts['rows'] += 1
                for record in row['records']:
                    counts[record['role']] += 1
                    counts['parameters'] += len(record['parameters'])
                    self.assertEqual(record['meaning'], 'unknown')
        self.assertEqual(counts, {'rows': 398, 'condition': 765, 'action': 968, 'parameters': 1475})
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(events.event_document(self.reader, raw), doc)
