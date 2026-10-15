import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave
import io

from tools import import_arena as arena
from tools import image_dump


def fixture(path):
    source = {'sha256': 'synthetic-arena'}
    header = bytearray(68)
    struct.pack_into('<H', header, 42, 0x101)
    struct.pack_into('<H', header, 54, 1)
    local = bytearray(header)
    struct.pack_into('<H', local, 54, 999)  # Deliberately stale local artwork.
    shape = {'header_hex': header.hex(), 'artwork': {'kind': 'image', 'image_id': 1}}
    stale = {'header_hex': local.hex(), 'artwork': {'kind': 'image', 'image_id': 999}}
    names = ['snowfloor']
    names += [f'P{p} {part}' for p in (1, 2) for part in ('Foot', 'body', 'Hand', 'hat', 'shoothand')]
    names += ['IceGun', 'Flame Thrower', 'Rocket Launcher', 'Health 25', 'Jetpack', 'bullet', 'Flame', 'Rocket']
    globals_ = [{'id': n, 'name': name, 'type': 1 if n == 0 else 2} for n, name in enumerate(names)]
    objects = [{'id': 0, 'name': 'snowfloor', 'type': 1, 'global': True},
               {'id': 1, 'name': 'P1h', 'type': 2, 'global': False},
               {'id': 2, 'name': 'P2h', 'type': 2, 'global': False},
               {'id': 3, 'name': 'BrickBack', 'type': 1, 'global': False}]
    records = []
    for ident, x, y in ((0, 80, 200), (1, 100, 120), (2, 200, 120), (3, 300, 200)):
        raw = bytearray(32)
        struct.pack_into('<Hhh', raw, 0, ident, x, y)
        records.append({'raw_hex': raw.hex()})
    def document(**fields):
        return {'source': source, **fields}
    docs = {
        'project-index.json': document(frames=[{'object_lists': [objects]}], global_object_lists=[globals_]),
        'frame-layout.json': document(frames=[{'dimension_inputs': {'width': {'raw_u16': 800}, 'height': {'raw_u16': 600}}, 'placements': [{'records': records}]}]),
        'backdrops.json': document(frames=[{'object_lists': [{'objects': [{'id': 0, 'backdrop': stale}, {'id': 3, 'backdrop': {'header_hex': bytes(68).hex(), 'artwork': {'kind': 'image', 'image_id': 1}}}]}]}], global_object_lists=[{'objects': [{'id': 0, 'backdrop': shape}]}]),
        'animations.json': document(global_object_lists=[{'objects': [{'id': n, 'active_data': [{'animations': [{'id': 0, 'directions': [{'id': 0, 'image_ids': [1]}, {'id': 16, 'image_ids': [1]}]}]}]} for n in range(1, len(names))]}]),
        'image-manifest.json': document(banks=[{'segment_id': 21, 'entries': [{'id': 1, 'file': 'image-21-1.png', 'image': {'hot_spot_raw_u16': [4, 65535]}}]}]),
    }
    samples = io.BytesIO()
    with wave.open(samples, 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(22050)
        stream.writeframes(b'\0\0' * 64)
    entries = []
    files = {'image-21-1.png': image_dump.png(bytes([0, 0, 0, 0]) + bytes([180, 120, 240, 255]) * 511, 32, 16)}
    for n, name in enumerate(('woosh', 'laser2b', 'fireshot', 'rocket', 'au', 'bonus', 'gdie5')):
        file = f'sound-23-{n}.wav'
        h = bytes(10) + name.encode().ljust(16, b'\0')
        entries.append({'id': n, 'file': file, 'header_hex': h.hex()})
        files[file] = samples.getvalue()
    docs['audio-manifest.json'] = document(banks=[{'kind': 'sound', 'segment_id': 23, 'entries': entries}])
    files.update({name: json.dumps(doc).encode() for name, doc in docs.items()})
    manifest = {'bundle': 'research-v1', 'source': source, 'files': [{'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in files.items()]}
    path.mkdir()
    for name, raw in files.items():
        (path / name).write_bytes(raw)
    (path / 'manifest.json').write_text(json.dumps(manifest))
    return docs


class ArenaImportTests(unittest.TestCase):
    def test_global_link_mask_and_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'bundle')
            summary = arena.import_arena(root / 'bundle', root / 'output', 0)
            text = (root / 'output/arena.ff').read_text()
            self.assertEqual(summary['layers'], 2)
            self.assertEqual(summary['spawns'], 2)
            self.assertEqual(summary['collision_pixels'], 511)
            self.assertIn('layer 1 80 200 32 16 0', text)
            self.assertIn('mask 200 81 31 1', text)  # Transparent corner is open.
            self.assertNotIn('mask 200 300', text)  # Decorative wall stays open.
            self.assertIn('hot 1 4 -1', text)
            self.assertNotIn('999', text)
            before = {p.name: p.read_bytes() for p in (root / 'output').iterdir()}
            arena.import_arena(root / 'bundle', root / 'output', 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in (root / 'output').iterdir()})
            (root / 'output/arena.ff').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'different content'):
                arena.import_arena(root / 'bundle', root / 'output', 0)
            self.assertEqual((root / 'output/arena.ff').read_text(), 'changed')

    def test_moving_platform_uses_visible_partner_art(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = fixture(root / 'bundle')
            _, files, _ = arena.checked_bundle(root / 'bundle')
            globals_ = docs['project-index.json']['global_object_lists'][0]
            animations = docs['animations.json']['global_object_lists'][0]['objects']
            for name, image in [('mph', 1), ('mph 2', 2)]:
                ident = len(globals_)
                globals_.append({'id': ident, 'name': name, 'type': 2})
                animations.append({'id': ident, 'active_data': [{'animations': [{'id': 0, 'directions': [{'id': 0, 'image_ids': [image]}]}]}]})
            docs['image-manifest.json']['banks'][0]['entries'].append({'id': 2, 'file': 'image-21-2.png', 'image': {'hot_spot_raw_u16': [4, 0]}})
            files['image-21-2.png'] = files['image-21-1.png']
            docs['project-index.json']['frames'][0]['object_lists'][0].append({'id': 4, 'name': 'mph', 'type': 2, 'global': True})
            raw = bytearray(32)
            struct.pack_into('<Hhh', raw, 0, 4, 200, 300)
            docs['frame-layout.json']['frames'][0]['placements'][0]['records'].append({'raw_hex': raw.hex()})
            docs['project-index.json']['frames'][0]['object_lists'][0].append({'id': 5, 'name': 'reverse', 'type': 2, 'global': True})
            for x in (100, 400):
                raw = bytearray(32)
                struct.pack_into('<Hhh', raw, 0, 5, x, 300)
                docs['frame-layout.json']['frames'][0]['placements'][0]['records'].append({'raw_hex': raw.hex()})
            text, _, report = arena.import_lines(files, docs, 0)
            self.assertIn('device 9 196 300 32 16 2', text)
            self.assertIn('path 0 96 396 1 -1', text)
            self.assertEqual(report['devices'], 1)

    def test_hidden_platform_direction_and_changer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = fixture(root / 'bundle')
            _, files, _ = arena.checked_bundle(root / 'bundle')
            globals_ = docs['project-index.json']['global_object_lists'][0]
            ident = len(globals_)
            globals_.append({'id': ident, 'name': 'up', 'type': 2})
            docs['animations.json']['global_object_lists'][0]['objects'].append({
                'id': ident, 'active_data': [{'animations': [{'id': 0, 'directions': [
                    {'id': 24, 'image_ids': [2]}, {'id': 16, 'image_ids': [3]}]}]}]})
            for image, width in ((2, 64), (3, 32)):
                files[f'image-21-{image}.png'] = image_dump.png(bytes([255, 0, 0, 255])*width*5, width, 5)
                docs['image-manifest.json']['banks'][0]['entries'].append({
                    'id': image, 'file': f'image-21-{image}.png', 'image': {'hot_spot_raw_u16': [0, 0]}})
            docs['project-index.json']['frames'][0]['object_lists'][0] += [
                {'id': 4, 'name': 'up', 'type': 2, 'global': True},
                {'id': 5, 'name': 'Changer', 'type': 2, 'global': True}]
            for obj, x in ((4, 400), (4, 600), (5, 400)):
                raw = bytearray(32)
                struct.pack_into('<Hhh', raw, 0, obj, x, 200)
                struct.pack_into('<H', raw, 24, 24)
                docs['frame-layout.json']['frames'][0]['placements'][0]['records'].append({'raw_hex': raw.hex()})
            text, wanted, report = arena.import_lines(files, docs, 0)
            self.assertEqual(report['collision_markers'], 2)
            self.assertIn('mask 200 400 32 2', text)
            self.assertIn('mask 200 600 64 2', text)
            self.assertIn('image-21-2.png', wanted)
            self.assertIn('image-21-3.png', wanted)
            self.assertNotIn('device ', text)  # Hidden markers never become visible devices.

    def test_invalid_bundle_no_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'bundle')
            image = root / 'bundle/image-21-1.png'
            image.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                arena.import_arena(root / 'bundle', root / 'output', 0)
            self.assertFalse((root / 'output').exists())
            image.unlink()
            image.symlink_to('/does-not-exist')
            with self.assertRaisesRegex(ValueError, 'symlinked'):
                arena.import_arena(root / 'bundle', root / 'output', 0)

    def test_wrong_global_link_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = fixture(root / 'bundle')
            _, files, _ = arena.checked_bundle(root / 'bundle')
            docs['project-index.json']['global_object_lists'][0][0]['name'] = 'other'
            with self.assertRaisesRegex(ValueError, 'global backdrop link'):
                arena.import_lines(files, docs, 0)

    def test_atomic_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'bundle')
            with patch.object(Path, 'rename', side_effect=OSError('deliberate rename fault')):
                with self.assertRaises(OSError):
                    arena.import_arena(root / 'bundle', root / 'output', 0)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['bundle'])

    def test_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'bundle')
            path = root / 'bundle/manifest.json'
            manifest = json.loads(path.read_text())
            manifest['files'][0]['file'] = '../outside'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'filename'):
                arena.import_arena(root / 'bundle', root / 'output', 0)

    def test_png_rejects_corruption(self):
        valid = image_dump.png(bytes([20, 40, 60, 255]) * 4, 2, 2)
        self.assertEqual(arena.rgba_png(valid), (2, 2, bytes([20, 40, 60, 255]) * 4))
        with self.assertRaises(ValueError):
            arena.rgba_png(valid[:-1])
        damaged = bytearray(valid)
        damaged[20] ^= 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            arena.rgba_png(bytes(damaged))

    def test_unexpected_write_fault_reports_without_private_context(self):
        with patch('sys.argv', ['import_arena', '--bundle', 'local-bundle']), \
             patch.object(arena, 'import_arena', side_effect=OSError('private path/token')), \
             patch.object(arena.project, 'report_fault') as reporter:
            self.assertEqual(arena.main(), 1)
        reporter.assert_called_once_with('OSError', version='arena-import/2', title='Arena import failed')

    @unittest.skipUnless(os.environ.get('FF_NATIVE_GAME'), 'native binary not supplied')
    def test_real_renderer_with_synthetic_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'bundle')
            arena.import_arena(root / 'bundle', root / 'output', 0)
            env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
            args = [os.environ['FF_NATIVE_GAME'], '--data', str(root / 'output'), '--smoke', '1000']
            a = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
            b = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(b.returncode, 0, b.stderr)
            self.assertEqual(a.stdout, b.stdout)

    @unittest.skipUnless(os.environ.get('FF_TEST_BUNDLE'), 'local original bundle not supplied')
    def test_local_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = arena.import_arena(Path(os.environ['FF_TEST_BUNDLE']), root / 'output')
            self.assertEqual(report['layers'], 512)
            self.assertGreaterEqual(report['spawns'], 2)
            self.assertIn('sprite 0 0', (root / 'output/arena.ff').read_text())


if __name__ == '__main__':
    unittest.main()
