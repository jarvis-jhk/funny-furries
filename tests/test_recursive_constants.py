import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import event_dump as events, export_project, project_index as project
from test_event_dump import reconstruct_program
from test_event_expressions import token, expression, expression_project, reconstruct_expression
from test_integer_constants import number, result


def group(items, stop=0xFEFF, negate=False):
    return ([token(0x400)] if negate else []) + [token(0xFFFF)] + items + [token(stop)]


class RecursiveConstantTests(unittest.TestCase):
    def test_both_stops_grouped_priorities_prefix_and_adjacent_groups(self):
        for stop in (0xFEFF, 0xFDFF):
            cases = [(group([number(7), token(0x200), number(3)], stop) + [token(0x600), number(5)], 50),
                     ([number(7), token(0x200)] + group([number(3), token(0x600), number(5)], stop), 22),
                     (group([number(7), token(0x200), number(3)], stop, True) + [token(0x600), number(5)], -50),
                     (group([number(20), token(0x600), number(7), token(0x800), number(3)], stop), 40),
                     (group([number(20)], stop) + [token(0x400)] + group([number(7)], stop), 13),
                     (group(group([number(2)], 0xFDFF, True), 0xFEFF, True), 2)]
            for items, expected in cases:
                with self.subTest(stop=stop, items=items):
                    self.assertEqual(result(items)['value_signed_i32'], expected)

    def test_recursive_numeric_boundaries_wrap_round_zero_and_prefix(self):
        for stop in (0xFEFF, 0xFDFF):
            for value in (-2147483648, -65537, -1, 0, 1, 65536, 2147483647):
                self.assertEqual(result(group([number(value)], stop, True))['value_raw_u32'], (-value) & 0xFFFFFFFF)
            cases = [(group([number(2147483647), token(0x200), number(1)], stop) + [token(0x400), number(1)], 2147483647),
                     ([number(65536), token(0x600)] + group([number(65536)], stop), 0),
                     (group([number(-7), token(0x800), number(3)], stop, True), 2),
                     (group([number(-7), token(0xA00), number(3)], stop), -1),
                     (group([number(-2147483648), token(0x800), number(0)], stop), 0),
                     (group([number(-2147483648), token(0xA00), number(0)], stop), -2147483648)]
            for items, expected in cases:
                self.assertEqual(result(items)['value_signed_i32'], expected)

    def test_fault_order_reduces_pending_outer_operator_before_next_operand(self):
        for stop in (0xFEFF, 0xFDFF):
            for code in (0x200, 0x400, 0x600, 0x800, 0xA00):
                items = ([number(-2147483648), token(0x800), number(-1), token(code)]
                         + group([number(-2147483648), token(0xA00), number(-1)], stop))
                out = result(items)
                self.assertEqual(out['status'], 'cpu_exception')
                self.assertEqual(out['operator_token_id'], 6 if code > 0x800 else 1)
                self.assertEqual(out['exception_recovery'], 'unknown')
                self.assertNotIn('value_signed_i32', out)
            self.assertEqual(result(group([number(-2147483648), token(0x800), number(-1)], stop)
                                    + [token(0x200)] + group([number(-2147483648), token(0xA00), number(-1)], stop))['operator_token_id'], 2)

    def test_complete_shape_validation_precedes_nested_arithmetic(self):
        trap = group([number(-2147483648), token(0x800), number(-1)])
        malformed = [[], [token(0xFFFF)], group([]), group([token(0x400)]),
                     [token(0xFFFF), number(1)], [number(1), token(0xFEFF)],
                     group([number(1)]) + [token(0xFDFF)], [token(0xFEFF)],
                     [number(1)] + group([number(2)]), group([number(1), number(2)]),
                     [token(0x400), token(0x400)] + group([number(1)]),
                     trap + [token(0x200)], trap + [token(0xFEFF)],
                     group(trap + [token(0x600)])]
        for items in malformed:
            with self.subTest(items=items):
                self.assertEqual(result(items), {'status': 'unsupported_shape'})
        unknown = trap + [token(0x200)] + group([token(0xC00), token(0x3FF, b'x\0')])
        self.assertEqual(result(unknown), {'status': 'unsupported_tokens', 'token_ids': [7, 8]})

    def test_deep_iterative_nesting_preserves_raw_controls_and_opaque_tail(self):
        depth = 4096
        items = [token(0xFFFF)] * depth + [number(17)] + [token(0xFEFF), token(0xFDFF)] * (depth // 2)
        raw = expression(items, prefix=0xBEEF, suffix=number(999) + b'opaque')
        out = events.decode_expression(raw)
        self.assertEqual(out['constant_integer_evaluation']['value_signed_i32'], 17)
        self.assertEqual(out['prefix_raw_u16'], 0xBEEF)
        self.assertEqual(reconstruct_expression(out), raw)
        self.assertTrue(all(t['meaning'] == 'unknown' for t in out['tokens']))
        self.assertEqual(sum('expression_control' in t for t in out['tokens']), depth * 2)


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class RecursiveConstantContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_expression_types_roles_scopes_readable_and_lossless(self):
        payload = expression(group([number(7), token(0x200), number(3)], 0xFDFF) + [token(0x600), number(5)])
        for kind in sorted(events.EXPRESSION_TYPES):
            raw, program = expression_project(payload)
            old = struct.pack('<HH', len(payload) + 4, 22)
            new = struct.pack('<HH', len(payload) + 4, kind)
            raw, program = raw.replace(old, new), program.replace(old, new)
            doc = events.event_document(self.reader, raw)
            self.assertTrue(doc['coverage']['recursive_integer_constants'])
            self.assertFalse(doc['coverage']['expression_evaluation'])
            self.assertFalse(doc['coverage']['parameter_semantics'])
            for prog in [p for f in doc['frames'] for p in f['programs']] + doc['global_events']:
                self.assertEqual(reconstruct_program(prog), program)
                for rec in prog['rows'][0]['records']:
                    out = rec['parameters'][0]['expression_storage']
                    self.assertEqual(out['constant_integer_evaluation']['value_signed_i32'], 50)
                    self.assertEqual(reconstruct_expression(out), payload)
            self.assertEqual(events.readable(doc).count('"value_signed_i32": 50'), 10)

    def test_immutable_bundle_repeat_and_research_faults_do_not_report(self):
        for items, status in [(group([number(7)], negate=True), 'value'),
                              (group([number(-2147483648), token(0x800), number(-1)]), 'cpu_exception'),
                              ([token(0xFFFF), number(1)], 'unsupported_shape')]:
            raw, _ = expression_project(expression(items))
            with patch.object(project, 'report_fault') as report:
                doc = events.event_document(self.reader, raw)
                manifest, files = export_project.research_bundle(self.reader, raw)
                self.assertEqual(files['events.json'], export_project.json_bytes(doc))
                self.assertEqual(files['events.txt'], events.readable(doc).encode())
                self.assertIn(('"status": "' + status + '"').encode(), files['events.txt'])
                scratch_root = project.REPO / 'build'
                scratch_root.mkdir(exist_ok=True)
                with tempfile.TemporaryDirectory(dir=scratch_root) as scratch:
                    target = export_project.save_bundle(manifest, files, Path(scratch))
                    first = {p.name: p.read_bytes() for p in target.iterdir()}
                    export_project.save_bundle(*export_project.research_bundle(self.reader, raw), Path(scratch))
                    self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, first)
                report.assert_not_called()

    def test_late_malformed_control_extent_refuses_every_output_and_reporting(self):
        payload = expression(group([number(7)]))
        raw, _ = expression_project(payload)
        # Change only the last control extent after several valid frame/global
        # programs; every entry point must refuse before writing its output.
        at = raw.rfind(token(0xFEFF))
        self.assertGreater(at, 0)
        broken = raw[:at + 2] + struct.pack('<H', 5) + raw[at + 4:]
        for module, flags in [(events, []), (events, ['--text']), (export_project, [])]:
            with patch.object(module.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused', *flags]), \
                    patch.object(project, 'load_reader', return_value=self.reader), \
                    patch.object(Path, 'read_bytes', return_value=broken), \
                    patch.object(project, 'save_export') as save, \
                    patch.object(export_project, 'save_bundle') as bundle, \
                    patch.object(project, 'report_fault') as report:
                self.assertEqual(module.main(), 2)
                save.assert_not_called()
                bundle.assert_not_called()
                report.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_control_words_remain_dynamic_and_byte_exact(self):
        raw = Path(os.environ['FF_TEST_PROJECT']).read_bytes()
        game = self.reader.read(raw)
        doc = events.event_document(self.reader, raw)
        programs = []
        for frame, level in zip(doc['frames'], game.levels()):
            blocks = self.reader.level_blocks(level.data)[1]
            for prog in frame['programs']:
                data = blocks[prog['block_id']].data
                programs.append((prog, data[prog['program_offset']:prog['program_offset'] + prog['program_bytes']]))
        for prog in doc['global_events']:
            data = game.segments[prog['segment_id']].data
            programs.append((prog, data[prog['program_offset']:prog['program_offset'] + prog['program_bytes']]))
        controls = {0xFFFF: 0, 0xFEFF: 0, 0xFDFF: 0}
        expressions = 0
        for prog, data in programs:
            self.assertEqual(reconstruct_program(prog), data)
            for row in prog['rows']:
                for rec in row['records']:
                    for param in rec['parameters']:
                        if param['type'] not in (15, 22, 23, 45, 52, 53):
                            continue
                        expressions += 1
                        at, end = param['offset'] + 6, param['offset'] + param['bytes']
                        codes = []
                        while at + 2 <= end:
                            code = int.from_bytes(data[at:at + 2], 'little')
                            if code == 0:
                                break
                            size = int.from_bytes(data[at + 2:at + 4], 'little')
                            self.assertGreaterEqual(size, 4)
                            self.assertLessEqual(at + size, end)
                            codes.append(code)
                            if code in controls:
                                controls[code] += 1
                            at += size
                        if any(code in controls for code in codes):
                            supported = {0xFF, 0x200, 0x400, 0x600, 0x800, 0xA00, *controls}
                            unknown_ids = [i for i, code in enumerate(codes) if code not in supported]
                            self.assertTrue(unknown_ids)
                            out = param['expression_storage']
                            self.assertEqual(out['constant_integer_evaluation'],
                                             {'status': 'unsupported_tokens', 'token_ids': unknown_ids})
                            self.assertEqual(reconstruct_expression(out), bytes.fromhex(param['payload_hex']))
        self.assertEqual(expressions, 3868)
        self.assertEqual(controls, {0xFFFF: 4, 0xFEFF: 105, 0xFDFF: 17})
        self.assertEqual(Path(os.environ['FF_TEST_PROJECT']).read_bytes(), raw)
