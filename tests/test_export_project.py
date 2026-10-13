import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from tools import export_project as exporter, project_index as project
from test_animation_dump import active_data
from test_audio_dump import audio_record, bank, midi, pcm
from test_backdrop_dump import header as backdrop_header
from test_display_dump import display_data
from test_event_dump import event_block, global_block, record, row, reconstruct_program
from test_frame_layout import placement_block, reconstruct as reconstruct_placements
from test_image_dump import EXPECTED, read_png, record as image_record


def combined_project(bad_image=False, empty=False):
    def block(kind, data):
        return struct.pack('<HI', kind, len(data)) + data
    def obj(kind, data):
        head = bytearray(68)
        head[42] = kind
        return bytes(head) + block(0x8000, data)
    program = row([record('condition', 2, -17, 0, [(999, b'own data')])],
                  [record('action', -3, 7, 0, [])]) + bytes(2)
    objects = struct.pack('<HH', 4, 0) + obj(2, active_data())
    objects += backdrop_header(1, image=5) + obj(7, display_data()) + backdrop_header(255)
    placement = placement_block([32, 0xFFFFFFFF, 0, 32], bytes(range(64)))
    frames = [bytes(184) + block(0x8000, b'palette'),
              bytes(184) + block(2, objects) + block(3, placement) + block(0x8004, event_block(program))]
    segments = [(3, global_block(program))] + [(8, f) for f in frames]
    segments += [(10, bank({2: image_record(), 5: image_record(True)})),
                 (13, bank({1: pcm()})), (12, bank({3: audio_record(2, midi())})),
                 (13, bank({})), (10, bank({7: b'bad' if bad_image else image_record()}))]
    if empty:
        frames, segments = [], [(10, bank({})), (12, bank({})), (13, bank({}))]
    header = bytearray(0x166 + 4 * len(frames))
    header[:4] = b'GAME'
    struct.pack_into('<H', header, 4, 0x0207)
    struct.pack_into('<H', header, 0x15C, len(frames))
    body, frame_id = b'', 0
    for n, (kind, payload) in enumerate(segments):
        if kind == 8:
            struct.pack_into('<I', header, 0x166 + 4 * frame_id, len(header) + len(body) + 6)
            frame_id += 1
        body += block(kind | (0x8000 if n == len(segments) - 1 else 0), payload)
    return bytes(header) + body, program, placement


def small_bundle():
    files = {'own.bin': b'own synthetic bytes'}
    manifest = {'source': {'sha256': 'a' * 64}, 'files': [
        {'file': 'own.bin', 'bytes': len(files['own.bin']),
         'sha256': hashlib.sha256(files['own.bin']).hexdigest()}]}
    files['manifest.json'] = exporter.json_bytes(manifest)
    return manifest, files


class BundleOutputTests(unittest.TestCase):
    def setUp(self):
        (project.REPO / 'build').mkdir(exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=project.REPO / 'build')
        self.addCleanup(self.scratch.cleanup)
        self.repo = Path(self.scratch.name)
        self.manifest, self.files = small_bundle()

    def test_immutable_repeat_and_changed_missing_extra_symlink_directory_files(self):
        target = exporter.save_bundle(self.manifest, self.files, self.repo)
        self.assertEqual(exporter.save_bundle(self.manifest, self.files, self.repo), target)
        item = target / 'own.bin'
        mutations = ['modified', 'missing', 'extra', 'symlink', 'directory']
        victim = self.repo / 'victim'
        victim.write_bytes(b'keep')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                if mutation == 'modified':
                    item.write_bytes(b'changed')
                elif mutation == 'missing':
                    item.unlink()
                elif mutation == 'extra':
                    (target / 'extra').write_bytes(b'x')
                elif mutation == 'symlink':
                    item.unlink()
                    item.symlink_to(victim)
                else:
                    item.unlink()
                    item.mkdir()
                before = (target / 'manifest.json').read_bytes()
                with self.assertRaises(project.InputError):
                    exporter.save_bundle(self.manifest, self.files, self.repo)
                self.assertEqual((target / 'manifest.json').read_bytes(), before)
                self.assertEqual(victim.read_bytes(), b'keep')
                if mutation == 'extra':
                    (target / 'extra').unlink()
                elif mutation == 'directory':
                    item.rmdir()
                elif mutation == 'symlink':
                    item.unlink()
                item.write_bytes(self.files['own.bin'])
        target.rename(self.repo / 'saved')
        target.write_bytes(b'keep non-directory')
        with self.assertRaises(project.InputError):
            exporter.save_bundle(self.manifest, self.files, self.repo)
        self.assertEqual(target.read_bytes(), b'keep non-directory')

    def test_late_write_and_rename_faults_leave_no_partial_tree(self):
        original_write = Path.write_bytes
        def late_failure(path, payload):
            if path.name == 'manifest.json':
                raise OSError('deliberate write failure after first file')
            return original_write(path, payload)
        for operation in [patch.object(Path, 'write_bytes', late_failure),
                          patch.object(Path, 'rename', side_effect=OSError('deliberate rename failure'))]:
            with operation, self.assertRaises(OSError):
                exporter.save_bundle(self.manifest, self.files, self.repo)
            directory = self.repo / 'export' / ('a' * 64)
            self.assertEqual(list(directory.iterdir()), [])
        target = exporter.save_bundle(self.manifest, self.files, self.repo)
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, self.files)

    def test_invalid_paths_manifest_hashes_and_symlink_roots_refused(self):
        for bad_sha in ['../escape', 'A' * 64, 'a' * 63, 123]:
            manifest = {**self.manifest, 'source': {'sha256': bad_sha}}
            with self.assertRaises(project.InputError):
                exporter.save_bundle(manifest, self.files, self.repo)
        for name in ['../escape', '/escape', '.', 'a/b', 'a\\b']:
            with self.assertRaises(project.InputError):
                exporter.save_bundle(self.manifest, {**self.files, name: b'x'}, self.repo)
        for files in [{**self.files, 'own.bin': b'wrong'},
                      {**self.files, 'manifest.json': b'{}'}, {}]:
            with self.assertRaises(project.InputError):
                exporter.save_bundle(self.manifest, files, self.repo)
        self.assertEqual(list(self.repo.iterdir()), [])
        for depth in [1, 2, 3]:
            with tempfile.TemporaryDirectory(dir=self.repo) as scratch:
                repo = Path(scratch)
                paths = [repo / 'export', repo / 'export' / ('a' * 64),
                         repo / 'export' / ('a' * 64) / exporter.BUNDLE]
                paths[depth - 1].parent.mkdir(parents=True, exist_ok=True)
                victim = repo / 'victim'
                victim.mkdir()
                paths[depth - 1].symlink_to(victim, target_is_directory=True)
                with self.assertRaises(project.InputError):
                    exporter.save_bundle(self.manifest, self.files, repo)
                self.assertEqual(list(victim.iterdir()), [])

    def test_cli_unexpected_and_write_faults_report_only_exception_class(self):
        argv = ['export', 'unused', '--klikback-src', 'unused']
        with patch.object(exporter.sys, 'argv', argv), patch.object(project, 'report_fault') as report:
            with patch.object(project, 'load_reader', side_effect=RuntimeError('private')):
                self.assertEqual(exporter.main(), 1)
            report.assert_called_once_with('RuntimeError', version=exporter.VERSION,
                                          title='Project bundle exporter crashed')
            report.reset_mock()
            with patch.object(project, 'load_reader'), patch.object(Path, 'read_bytes', return_value=b''), \
                    patch.object(exporter, 'research_bundle', return_value=(self.manifest, self.files)), \
                    patch.object(exporter, 'save_bundle', side_effect=OSError('private')):
                self.assertEqual(exporter.main(), 1)
            report.assert_called_once_with('OSError', version=exporter.VERSION,
                                          title='Project bundle exporter crashed')
            report.reset_mock()
            with patch.object(project, 'load_reader', side_effect=project.InputError('bad input')):
                self.assertEqual(exporter.main(), 2)
            report.assert_not_called()


@unittest.skipUnless(os.environ.get('FF_KLIKBACK_SRC'), 'set FF_KLIKBACK_SRC for parser tests')
class CombinedExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = project.load_reader(Path(os.environ['FF_KLIKBACK_SRC']))

    def test_all_components_media_gaps_repeated_banks_and_lossless_events_placements(self):
        raw, program, placement = combined_project()
        manifest, files = exporter.research_bundle(self.reader, raw)
        self.assertEqual(exporter.research_bundle(self.reader, raw), (manifest, files))
        events = json.loads(files['events.json'])
        self.assertEqual(reconstruct_program(events['frames'][1]['programs'][0]), program)
        self.assertEqual(reconstruct_program(events['global_events'][0]), program)
        self.assertEqual(events['frames'][0]['programs'], [])
        placements = json.loads(files['frame-layout.json'])
        self.assertEqual(reconstruct_placements(placements['frames'][1]['placements'][0]), placement)
        self.assertEqual(json.loads(files['animations.json'])['frames'][1]['object_lists'][0]['objects'][0]
                         ['active_data'][0]['animations'][0]['directions'][0]['image_ids'], [2, 5, 5])
        image_manifest = json.loads(files['image-manifest.json'])
        self.assertEqual([[e['id'] for e in b['entries']] for b in image_manifest['banks']], [[2, 5], [7]])
        for entry in [e for b in image_manifest['banks'] for e in b['entries']]:
            self.assertEqual(read_png(files[entry['file']]), (3, 2, EXPECTED))
        audio = json.loads(files['audio-manifest.json'])
        self.assertEqual([[e['id'] for e in b['entries']] for b in audio['banks']], [[1], [3], []])
        sound, music = audio['banks'][0]['entries'][0], audio['banks'][1]['entries'][0]
        self.assertIn(music['file'], files)
        with wave.open(io.BytesIO(files[sound['file']]), 'rb') as wav:
            self.assertEqual(wav.readframes(wav.getnframes()), b'\0\x80\xff')
        self.assertEqual(files[music['file']], midi())
        self.assertIn(b'REFERENCE status=local_slot_match', files['events.txt'])
        self.assertEqual(len(manifest['files']) + 1, len(files))
        for entry in manifest['files']:
            self.assertEqual(hashlib.sha256(files[entry['file']]).hexdigest(), entry['sha256'])
        for name in manifest['components']:
            self.assertEqual(json.loads(files[name])['source'], manifest['source'])
        self.assertFalse(manifest['coverage']['behaviour'])

    def test_empty_banks_and_absent_frames_still_export_explicit_unknowns(self):
        raw, _, _ = combined_project(empty=True)
        manifest, files = exporter.research_bundle(self.reader, raw)
        self.assertEqual(len(files), 10)
        self.assertEqual(json.loads(files['events.json'])['frames'], [])
        self.assertEqual(json.loads(files['events.json'])['global_events'], [])
        self.assertEqual(json.loads(files['image-manifest.json'])['banks'][0]['entries'], [])
        self.assertFalse(manifest['coverage']['arena_geometry'])
        self.assertFalse(manifest['coverage']['playable_runtime'])

    def test_invalid_last_image_writes_nothing_and_does_not_report(self):
        raw, _, _ = combined_project(bad_image=True)
        with patch.object(exporter.sys, 'argv', ['export', 'unused', '--klikback-src', 'unused']), \
                patch.object(project, 'load_reader', return_value=self.reader), \
                patch.object(Path, 'read_bytes', return_value=raw), \
                patch.object(exporter, 'save_bundle') as save, patch.object(project, 'report_fault') as report:
            self.assertEqual(exporter.main(), 2)
            save.assert_not_called()
            report.assert_not_called()

    def test_component_fingerprint_mismatch_is_an_unexpected_fault(self):
        raw, _, _ = combined_project()
        original = exporter.display_dump.display_document(self.reader, raw)
        for field in ['source', 'reader_sha256']:
            wrong = copy.deepcopy(original)
            wrong[field] = {} if field == 'source' else 'b' * 64
            with patch.object(exporter.display_dump, 'display_document', return_value=wrong):
                with self.assertRaises(RuntimeError):
                    exporter.research_bundle(self.reader, raw)

    @unittest.skipUnless(os.environ.get('FF_TEST_PROJECT'), 'set FF_TEST_PROJECT for original verification')
    def test_original_complete_bundle_media_counts_and_atomic_readback(self):
        path = Path(os.environ['FF_TEST_PROJECT'])
        raw = path.read_bytes()
        manifest, files = exporter.research_bundle(self.reader, raw)
        self.assertEqual(manifest['source']['sha256'],
                         '98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0')
        images = json.loads(files['image-manifest.json'])
        audio = json.loads(files['audio-manifest.json'])
        self.assertEqual(sum(len(b['entries']) for b in images['banks']), 614)
        self.assertEqual(sum(len(b['entries']) for b in audio['banks']), 19)
        self.assertEqual(len(files), 643)
        for component in [images, audio]:
            for entry in [e for b in component['banks'] for e in b['entries']]:
                self.assertIn(entry['file'], files)
                payload = files[entry['file']]
                self.assertEqual(len(payload), entry['file_bytes'])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry['file_sha256'])
        # Read back each persisted file after the single directory installation.
        with tempfile.TemporaryDirectory(dir=project.REPO / 'build') as scratch:
            target = exporter.save_bundle(manifest, files, Path(scratch))
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, files)
            self.assertEqual(exporter.save_bundle(manifest, files, Path(scratch)), target)
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
