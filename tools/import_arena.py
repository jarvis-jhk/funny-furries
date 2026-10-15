#!/usr/bin/env python3
"""Turn a user's research-v1 bundle into local data for the M1 SDL prototype."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import project_index as project

W, H = 800, 600


def rgba_png(raw: bytes):
    """Read only the RGBA/filter-zero dialect written by our image exporter."""
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('not an exported PNG')
    cursor, width, height, compressed = 8, 0, 0, bytearray()
    ended = False
    while cursor + 12 <= len(raw):
        size, = struct.unpack_from('>I', raw, cursor)
        kind = raw[cursor + 4:cursor + 8]
        body = raw[cursor + 8:cursor + 8 + size]
        if len(body) != size or cursor + size + 12 > len(raw):
            raise ValueError('truncated PNG')
        crc, = struct.unpack_from('>I', raw, cursor + 8 + size)
        if zlib.crc32(kind + body) != crc:
            raise ValueError('PNG checksum mismatch')
        if kind == b'IHDR':
            width, height, depth, mode, comp, filt, interlace = struct.unpack('>IIBBBBB', body)
            if not (0 < width <= 4096 and 0 < height <= 4096) or (depth, mode, comp, filt, interlace) != (8, 6, 0, 0, 0):
                raise ValueError('unsupported PNG dialect')
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            ended = cursor + 12 == len(raw) and size == 0
            break
        cursor += size + 12
    if not ended or not width or not height:
        raise ValueError('incomplete PNG')
    expected = height * (width * 4 + 1)
    decoder = zlib.decompressobj()
    scan = decoder.decompress(compressed, expected + 1)
    if len(scan) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError('PNG scanline extent mismatch')
    stride = width * 4 + 1
    if any(scan[y * stride] for y in range(height)):
        raise ValueError('unsupported PNG row filter')
    return width, height, b''.join(scan[y * stride + 1:(y + 1) * stride] for y in range(height))


def checked_bundle(path: Path):
    manifest = json.loads((path / 'manifest.json').read_text())
    if manifest.get('bundle') != 'research-v1':
        raise ValueError('expected a research-v1 bundle')
    files = {}
    for entry in manifest['files']:
        name = entry['file']
        if not isinstance(name, str) or Path(name).name != name or '\\' in name or name in {'.', '..'} or name in files:
            raise ValueError('invalid or repeated bundle filename')
        source = path / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('bundle contains a missing or symlinked file')
        raw = source.read_bytes()
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('bundle file checksum mismatch')
        files[name] = raw
    required = ('project-index.json', 'frame-layout.json', 'backdrops.json', 'animations.json', 'image-manifest.json', 'audio-manifest.json')
    documents = {name: json.loads(files[name]) for name in required}
    if any(d['source']['sha256'] != manifest['source']['sha256'] for d in documents.values()):
        raise ValueError('mixed source bundle')
    return manifest, files, documents


def signed16(value):
    return value - 65536 if value >= 32768 else value


def import_lines(files, docs, frame):
    index = docs['project-index.json']
    layouts = docs['frame-layout.json']
    if not 0 <= frame < len(index['frames']):
        raise ValueError('frame does not exist')
    layout = layouts['frames'][frame]
    size = layout['dimension_inputs']
    if (size['width']['raw_u16'], size['height']['raw_u16']) != (W, H):
        raise ValueError('M1 supports 800x600 arenas only')
    objects = index['frames'][frame]['object_lists']
    if len(objects) != 1:
        raise ValueError('ambiguous frame object lists')
    names = {o['id']: o for o in objects[0]}
    backdrop_lists = docs['backdrops.json']['frames'][frame]['object_lists']
    if len(backdrop_lists) != 1:
        raise ValueError('ambiguous backdrop lists')
    backdrops = {o['id']: o['backdrop'] for o in backdrop_lists[0]['objects'] if o['backdrop']}
    banks = docs['image-manifest.json']['banks']
    if len(banks) != 1 or banks[0]['segment_id'] != 21:
        raise ValueError('M1 needs one image bank at segment 21')
    images = {e['id']: e for e in banks[0]['entries']}
    if len(index['global_object_lists']) != 1 or len(docs['backdrops.json']['global_object_lists']) != 1:
        raise ValueError('M1 needs one global object list')
    global_definitions = {o['id']: o for o in index['global_object_lists'][0]}
    global_backdrops = {o['id']: o['backdrop'] for o in docs['backdrops.json']['global_object_lists'][0]['objects'] if o['backdrop']}
    pixels = {}
    wanted = set()
    lines = ['FFARENA 1', '# Locally imported original content; never redistribute.']
    collisions = [bytearray(W) for _ in range(H)]
    spawns = []
    initial = {}
    active_placements = []
    layers = 0

    def image_info(image_id):
        info = images[image_id]
        if not 0 <= image_id < 1024:
            raise ValueError('image handle exceeds native capacity')
        wanted.add(info['file'])
        if image_id not in pixels:
            pixels[image_id] = rgba_png(files[info['file']])
        return pixels[image_id]

    for placement in layout['placements']:
        for record in placement['records']:
            raw = bytes.fromhex(record['raw_hex'])
            ident, x, y = struct.unpack_from('<Hhh', raw)
            if ident not in names:
                raise ValueError('placement has no local definition')
            name = names[ident]['name']
            active_placements.append((name, x, y))
            if name == 'Start' and 12 <= x <= 788 and 32 <= y + 16 <= 560:
                spawns.append((x, y + 16))
            if name in {'P1h', 'P2h'}:
                initial[name] = (x, y + 16)
            if ident not in backdrops:
                continue
            backdrop = backdrops[ident]
            header = bytes.fromhex(backdrop['header_hex'])
            if names[ident]['global']:
                global_id, = struct.unpack_from('<H', header, 40)
                definition = global_definitions.get(global_id)
                if not definition or (definition['name'], definition['type']) != (name, names[ident]['type']) or global_id not in global_backdrops:
                    raise ValueError('global backdrop link disagrees with name/type')
                backdrop = global_backdrops[global_id]
                header = bytes.fromhex(backdrop['header_hex'])
            artwork = backdrop['artwork']
            image_id = artwork['image_id']
            kind = artwork['kind']
            if kind in {'image', 'mosaic'}:
                iw, ih, rgba = image_info(image_id)
            else:
                image_id, iw, ih, rgba = -1, 0, 0, b''
            if kind == 'image':
                width, height, draw = iw, ih, 0
            else:
                width, height = struct.unpack_from('<HH', header, 34)
                draw = {'mosaic': 1, 'solid': 2, 'gradient': 3}[kind]
                if kind == 'gradient' and artwork['gradient_axis'] == 'horizontal':
                    draw = 4
            if not 1 <= width <= 4096 or not 1 <= height <= 4096:
                raise ValueError('invalid backdrop extent')
            colors = artwork.get('colors', [{'rgb': [0, 0, 0]}] * 2)
            rgb = [sum(c['rgb'][n] << (16 - n * 8) for n in range(3)) for c in colors]
            lines.append(f'layer {image_id} {x} {y} {width} {height} {draw} {rgb[0]:06x} {rgb[-1]:06x}')
            layers += 1
            flags = struct.unpack_from('<H', header, 42)[0]
            # Named foreground plus one header bit is an M1 approximation.
            # The original also uses active collision-marker objects.
            terrain = name.startswith(('snow', 'metal')) or name in {'Ice', 'Ice 2'}
            collision = (2 if flags & 0x100 else 1) if terrain else 0
            if collision:
                for yy in range(max(0, y), min(H, y + height)):
                    for xx in range(max(0, x), min(W, x + width)):
                        opaque = kind not in {'image', 'mosaic'} or rgba[((yy - y) % ih * iw + (xx - x) % iw) * 4 + 3] > 127
                        if opaque:
                            collisions[yy][xx] = min(collisions[yy][xx] or collision, collision)
    if not layers or layers > 2048:
        raise ValueError('missing arena scenery or layer capacity exceeded')

    def free_spawn(p):
        x, y = p
        return 12 <= x <= 788 and 32 <= y <= 560 and not any(1 in row[x - 11:x + 12] for row in collisions[y - 32:y])

    # Keep the two stored collision-body origins first, then respawn markers.
    # Exclude points embedded in walls; never spawn a player inside solid terrain.
    ordered = [initial[k] for k in ('P1h', 'P2h') if k in initial] + spawns
    usable = list(dict.fromkeys(p for p in ordered if free_spawn(p)))
    if not 2 <= len(usable) <= 64:
        raise ValueError('arena lacks two usable player spawn points')
    lines += [f'spawn {x} {y}' for x, y in usable]
    for y, row in enumerate(collisions):
        x = 0
        while x < W:
            if not row[x]:
                x += 1
                continue
            end = x + 1
            while end < W and row[end] == row[x]:
                end += 1
            lines.append(f'mask {y} {x} {end - x} {row[x]}')
            x = end

    global_names = {}
    global_animation = {}
    for group in index['global_object_lists']:
        for o in group:
            key = (o['name'], o['type'])
            if key in global_names:
                raise ValueError('ambiguous global artwork name')
            global_names[key] = o['id']
    for group in docs['animations.json']['global_object_lists']:
        for obj in group['objects']:
            if obj['active_data']:
                global_animation[obj['id']] = obj['active_data']

    def animations(name):
        ident = global_names[(name, 2)]
        data = global_animation[ident]
        if len(data) != 1:
            raise ValueError('ambiguous global animation body')
        return [a for a in data[0]['animations'] if a.get('directions')]

    for player in range(2):
        for part, suffix in enumerate(('Foot', 'body', 'Hand', 'hat', 'shoothand')):
            for anim in animations(f'P{player + 1} {suffix}'):
                for direction in anim['directions']:
                    if direction['id'] not in (0, 16) or not direction['image_ids']:
                        continue
                    if len(direction['image_ids']) > 32:
                        raise ValueError('animation exceeds native capacity')
                    for image in direction['image_ids']:
                        image_info(image)
                        lines.append(f'sprite {player} {part} {anim["id"]} {int(direction["id"] == 16)} {image}')

    def first_image(name):
        for anim in animations(name):
            for direction in anim['directions']:
                if direction['image_ids']:
                    result = direction['image_ids'][0]
                    image_info(result)
                    return result
        raise ValueError('missing active artwork')

    device_kinds = {'Water': 1, 'Fan L': 2, 'Fan R': 3, 'Fan up': 4,
                    'bounce up': 5, 'bounce down': 6, 'bounce L': 7,
                    'bounce R': 8, 'mph': 9}
    for name, x, y in active_placements:
        if name not in device_kinds:
            continue
        ident = first_image(name)
        width, height, _ = image_info(ident)
        hx, hy = map(signed16, images[ident]['image']['hot_spot_raw_u16'])
        lines.append(f'device {device_kinds[name]} {x-hx} {y-hy} {width} {height} {ident}')

    for kind, name in enumerate(('', 'IceGun', 'Flame Thrower', 'Rocket Launcher', 'Health 25', 'Jetpack')):
        if kind:
            lines.append(f'pickup {kind} {first_image(name)}')
    for kind, name in enumerate(('', 'bullet', 'Flame', 'Rocket')):
        if kind:
            lines.append(f'shot {kind} {first_image(name)}')
    for ident, info in images.items():
        if info['file'] in wanted:
            hx, hy = map(signed16, info['image']['hot_spot_raw_u16'])
            lines.append(f'hot {ident} {hx} {hy}')

    sounds = {}
    for bank in docs['audio-manifest.json']['banks']:
        if bank['kind'] == 'sound':
            if bank['segment_id'] != 23:
                raise ValueError('unsupported sound bank')
            for entry in bank['entries']:
                name = bytes.fromhex(entry['header_hex'])[10:26].split(b'\0', 1)[0].decode('latin1')
                sounds[name] = entry
    for sound, name in enumerate(('woosh', 'laser2b', 'fireshot', 'rocket', 'au', 'bonus', 'gdie5')):
        entry = sounds[name]
        wanted.add(entry['file'])
        lines.append(f'sound {sound} {entry["id"]}')
    return '\n'.join(lines) + '\n', wanted, {'frame': frame, 'layers': layers, 'spawns': len(usable), 'devices': sum(name in device_kinds for name, _, _ in active_placements), 'collision_pixels': sum(sum(bool(v) for v in row) for row in collisions)}


def import_arena(bundle: Path, output: Path, frame=3):
    manifest, files, docs = checked_bundle(bundle)
    text, wanted, summary = import_lines(files, docs, frame)
    payloads = {name: files[name] for name in sorted(wanted)}
    payloads['arena.ff'] = text.encode('ascii')
    report = {'importer': 'arena-import/1', 'source_sha256': manifest['source']['sha256'], **summary,
              'fidelity': 'prototype; collision flags, timing and feel need original-game acceptance',
              'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()}}
    payloads['import.json'] = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    if output.is_symlink():
        raise ValueError('output must not be a symlink')
    if output.exists():
        if {p.name for p in output.iterdir()} == set(payloads) and all(not (output / n).is_symlink() and (output / n).read_bytes() == raw for n, raw in payloads.items()):
            return report
        raise ValueError('output already exists with different content; choose a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.arena-', dir=output.parent) as temp:
        stage = Path(temp) / 'complete'
        stage.mkdir()
        for name, raw in payloads.items():
            (stage / name).write_bytes(raw)
        stage.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('export/arena-1'))
    parser.add_argument('--frame', type=int, default=3)
    args = parser.parse_args()
    try:
        summary = import_arena(args.bundle, args.output, args.frame)
    except (FileNotFoundError, ValueError, KeyError, IndexError, struct.error, zlib.error) as error:
        print(f'Import refused: {error}', file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version='arena-import/1', title='Arena import failed')
        print('Arena import failed; original input was not modified.', file=sys.stderr)
        return 1
    print(f'Imported frame {summary["frame"]}: {summary["layers"]} layers, {summary["spawns"]} spawn candidates.\nPlay: build/native/funny-furries --data {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
