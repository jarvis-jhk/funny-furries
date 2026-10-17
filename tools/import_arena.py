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
    required = ('project-index.json', 'frame-layout.json', 'backdrops.json', 'animations.json', 'image-manifest.json', 'audio-manifest.json', 'displays.json')
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

    def sequence(name, anim_id=0, direction=0):
        """Images and speed of one animation direction (speed = header byte 0)."""
        for a in animations(name):
            if a['id'] != anim_id:
                continue
            choices = [d for d in a['directions'] if d['image_ids']]
            if not choices:
                return None
            d = next((d for d in choices if d['id'] == direction), choices[0])
            speed = bytes.fromhex(d['header_hex'])[0] if d.get('header_hex') else 0
            for image in d['image_ids']:
                image_info(image)
            return max(1, min(100, speed)), d['image_ids'][:32]
        return None

    for placement in layout['placements']:
        for record in placement['records']:
            raw = bytes.fromhex(record['raw_hex'])
            ident, x, y = struct.unpack_from('<Hhh', raw)
            if ident not in names:
                raise ValueError('placement has no local definition')
            name = names[ident]['name']
            active_placements.append((name, x, y, struct.unpack_from('<H', raw, 24)[0]))
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
            # Foreground obstacles use bit 8; ordinary snow is supported by
            # separate hidden `up` objects, not by its decorative bitmap.
            collision = 1 if flags & 0x100 else 0
            if collision:
                for yy in range(max(0, y), min(H, y + height)):
                    for xx in range(max(0, x), min(W, x + width)):
                        opaque = kind not in {'image', 'mosaic'} or rgba[((yy - y) % ih * iw + (xx - x) % iw) * 4 + 3] > 127
                        if opaque:
                            collisions[yy][xx] = min(collisions[yy][xx] or collision, collision)
    if not layers or layers > 2048:
        raise ValueError('missing arena scenery or layer capacity exceeded')

    def active_image(name, direction=0):
        choices = [d for a in animations(name) for d in a['directions'] if d['image_ids']]
        selected = next((d for d in choices if d['id'] == direction),
                        next((d for d in choices if d['id'] == 0), choices[0]))
        result = selected['image_ids'][0]
        image_info(result)
        return result

    markers = 0
    for name, x, y, direction in active_placements:
        if name not in {'up', 'Ice'} or (name, 2) not in global_names:
            continue
        # Start-of-frame Changer overlap selects the short (direction 16) top.
        initial_image = active_image(name, direction)
        width, height, _ = image_info(initial_image)
        hx, hy = map(signed16, images[initial_image]['image']['hot_spot_raw_u16'])
        if any(n == 'Changer' and x-hx <= cx < x-hx+width and y-hy <= cy < y-hy+height
               for n, cx, cy, _ in active_placements):
            direction = 16
        ident = active_image(name, direction)
        width, height, rgba = image_info(ident)
        hx, hy = map(signed16, images[ident]['image']['hot_spot_raw_u16'])
        for yy in range(max(0, y-hy), min(H, y-hy+height)):
            for xx in range(max(0, x-hx), min(W, x-hx+width)):
                if rgba[((yy-y+hy)*width+xx-x+hx)*4+3] > 127 and not collisions[yy][xx]:
                    collisions[yy][xx] = 2
        markers += 1

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
                    # Header: speed byte 0, repeat count u16 at 2 (0 loops for ever).
                    if not direction.get('header_hex'):
                        continue
                    header = bytes.fromhex(direction['header_hex'])
                    once = int(int.from_bytes(header[2:4], 'little') != 0)
                    lines.append(f'spritespeed {player} {part} {anim["id"]} {int(direction["id"] == 16)} {min(header[0], 100)} {once}')

    def first_image(name):
        return active_image(name)

    def active_bounds(name, direction=0):
        ident = active_image(name, direction)
        width, height, rgba = image_info(ident)
        points = [(xx, yy) for yy in range(height) for xx in range(width)
                  if rgba[(yy * width + xx) * 4 + 3] > 127]
        if not points:
            raise ValueError('empty moving-platform collision marker')
        hx, hy = map(signed16, images[ident]['image']['hot_spot_raw_u16'])
        return (min(p[0] for p in points)-hx, min(p[1] for p in points)-hy,
                max(p[0] for p in points)-hx, max(p[1] for p in points)-hy)

    device_kinds = {'Water': 1, 'Fan L': 2, 'Fan R': 3, 'Fan up': 4,
                    'bounce up': 5, 'bounce down': 6, 'bounce L': 7,
                    'bounce R': 8, 'mph': 9, 'Wind L': 10, 'Wind R': 11, 'Wind up': 12}
    device_count = 0
    animated = set()
    for name, x, y, direction in active_placements:
        if name not in device_kinds:
            continue
        ident = first_image('mph 2' if name == 'mph' else name)
        width, height, _ = image_info(ident)
        hx, hy = map(signed16, images[ident]['image']['hot_spot_raw_u16'])
        if x-hx >= W or y-hy >= 600 or x-hx+width <= 0 or y-hy+height <= 0:
            continue   # parked outside the frame (levels 8, 9 and 11 keep a spare platform below it)
        lines.append(f'device {device_kinds[name]} {x-hx} {y-hy} {width} {height} {ident if device_kinds[name] < 10 else -1}')
        kind = device_kinds[name]
        if kind < 10 and kind not in animated:
            animated.add(kind)
            for fired, anim_id in ((0, 0), (1, 12)):
                found = sequence('mph 2' if name == 'mph' else name, anim_id)
                if found and (fired or len(found[1]) > 1):
                    lines += [f'devanim {kind} {fired} {found[0]} {image}' for image in found[1]]
        if name == 'mph':
            px0, py0, px1, py1 = active_bounds('mph', direction)
            stops = []
            for n, rx, ry, rd in active_placements:
                if n != 'reverse':
                    continue
                rx0, ry0, rx1, ry1 = active_bounds(n, rd)
                if ry+ry0 <= y+py1 and ry+ry1 >= y+py0:
                    stops.append((rx, rx+rx0, rx+rx1))
            left = sorted(s for s in stops if s[0] <= x)
            right = sorted(s for s in stops if s[0] >= x)
            if not left or not right:
                raise ValueError('moving platform lacks surrounding reverse markers')
            low, high = left[-1][2]-hx-px0, right[0][1]-hx-px1
            if not low <= x-hx <= high or low >= high:
                raise ValueError('moving platform overlaps its reverse markers at start')
            # A Changer on the platform at the start sends it left; the others go right.
            def touches(n, cx, cy, cd):
                if n != 'Changer' or ('Changer', 2) not in global_names:
                    return False
                c0, c1, c2, c3 = active_bounds(n, cd)
                return cx+c0 <= x+px1 and cx+c2 >= x+px0 and cy+c1 <= y+py1 and cy+c3 >= y+py0
            heading = -1 if any(touches(*placement) for placement in active_placements) else 1
            lines.append(f'path {device_count} {low} {high} 1 {heading}')
        device_count += 1

    for kind, name in enumerate(('', 'IceGun', 'Flame Thrower', 'Rocket Launcher', 'Health 25', 'Jetpack')):
        if kind:
            lines.append(f'pickup {kind} {first_image(name)}')
            found = sequence(name)
            if found and len(found[1]) > 1:
                lines += [f'pickanim {kind} {found[0]} {image}' for image in found[1]]
    for kind, name in enumerate(('', 'bullet', 'Flame', 'Rocket')):
        if kind:
            lines.append(f'shot {kind} {first_image(name)}')
    for player in range(2):
        for a in animations(f'P{player+1} shoothand'):
            if a['id'] not in (13, 14, 15):
                continue
            kind = {13: 1, 14: 3, 15: 2}[a['id']]
            for d in a['directions']:
                if d['id'] not in (0, 16) or not d['image_ids']:
                    continue
                info = images[d['image_ids'][0]]['image']
                ax, ay = map(signed16, info['action_point_raw_u16'])
                hx, hy = map(signed16, info['hot_spot_raw_u16'])
                lines.append(f'muzzle {player} {kind} {int(d["id"] == 16)} {ax-hx} {ay-hy-16}')
    for name in ('P1 fly', 'P2 fly'):
        if (name, 2) in global_names:
            for d in next((a['directions'] for a in animations(name) if a['id'] == 0), []):
                if d['id'] in (0, 16) and d['image_ids']:
                    image_info(d['image_ids'][0])
                    lines.append(f'jetpack {int(d["id"] == 16)} {d["image_ids"][0]}')
            break
    if ('smoke', 2) in global_names:
        # The puffs the original's fly object leaves while the jetpack fires (frame rows 26/27).
        found = sequence('smoke', 0, 16)
        if found:
            lines += [f'smoke {found[0]} {image}' for image in found[1]]
    if ('Bubble', 2) in global_names:
        for popping, anim_id in ((0, 0), (1, 12)):
            found = sequence('Bubble', anim_id)
            if found:
                lines += [f'bubble {popping} {found[0]} {image}' for image in found[1]]
    for a in animations('Flame'):
        if a['id'] in (0, 12):
            for d in a['directions']:
                if d['image_ids']:
                    for image in d['image_ids']:
                        image_info(image)
                        lines.append(f'fire {int(a["id"] == 12)} {image}')
                    break
    for name, x, y, _ in active_placements:
        # Ten Bonus objects wait at exactly (0, 0) outside play; they are not spawn points.
        if name == 'Bonus' and 0 <= x < W and 0 <= y < 560 and (x, y) != (0, 0):
            lines.append(f'bonus {x} {y}')
    for kind, name in enumerate(('Bomb', 'Bombwalk', 'Bombfly'), 1):
        if (name, 2) not in global_names:
            continue
        for a in animations(name):
            if a['id'] != 0:
                continue
            for d in a['directions']:
                if d['id'] not in (0, 16):
                    continue
                for image in d['image_ids'] or []:
                    image_info(image)
                    lines.append(f'hazard {kind} {int(d["id"] == 16)} {image}')
            found = sequence(name)
            if found:
                lines.append(f'hazardspeed {kind} {found[0]}')
    if ('Explosion', 2) in global_names:
        for a in animations('Explosion'):
            if a['id'] == 0:
                for d in a['directions']:
                    if d['image_ids']:
                        for frame_id, image in enumerate(d['image_ids']):
                            width, height, _ = image_info(image)
                            lines.append(f'blast {image}')
                            info = images[image]['image']
                            hx, hy = map(signed16, info['hot_spot_raw_u16'])
                            lines.append(f'blastbox {frame_id} {-hx} {-hy} {width} {height}')
                        break
    lines += scoreboard(docs, active_placements, names, sequence, image_info)
    for ident, info in images.items():
        if info['file'] in wanted:
            hx, hy = map(signed16, info['image']['hot_spot_raw_u16'])
            lines.append(f'hot {ident} {hx} {hy}')

    # The title frame plays music 0, every arena music 1, both looping (frame rows "play music").
    for bank in docs['audio-manifest.json']['banks']:
        if bank['kind'] == 'music' and bank['segment_id'] == 22:
            for entry in bank['entries']:
                if entry['id'] in (0, 1) and entry['file'].endswith('.mid'):
                    wanted.add(entry['file'])
                    lines.append(f'music {entry["id"]} {entry["id"]}')
    sounds = {}
    for bank in docs['audio-manifest.json']['banks']:
        if bank['kind'] == 'sound':
            if bank['segment_id'] != 23:
                raise ValueError('unsupported sound bank')
            for entry in bank['entries']:
                name = bytes.fromhex(entry['header_hex'])[10:26].split(b'\0', 1)[0].decode('latin1')
                sounds[name] = entry
    for sound, name in enumerate(('woosh', 'laser2b', 'fireshot', 'rocket', 'au', 'bonus', 'gdie5', 'explod7')):
        if name == 'explod7' and name not in sounds:
            continue
        entry = sounds[name]
        wanted.add(entry['file'])
        lines.append(f'sound {sound} {entry["id"]}')
    # The original's event sounds: jump, landing, spring, splash, jetpack, shot on a wall, collecting, being hit.
    for sound, name in enumerate(('hup', 'land', 'spring03', 'h2ohit1', 'fly', 'lashit', 'ghealth', 'gdie2'), 16):
        if name in sounds:
            wanted.add(sounds[name]['file'])
            lines.append(f'sound {sound} {sounds[name]["id"]}')
    return '\n'.join(lines) + '\n', wanted, {'frame': frame, 'layers': layers, 'spawns': len(usable), 'devices': device_count, 'collision_markers': markers, 'collision_pixels': sum(sum(bool(v) for v in row) for row in collisions)}


def scoreboard(docs, placements, names, sequence, image_info):
    """The original two-player panel: counter places, digit images, weapon icons, bars.

    The panel itself is an ordinary backdrop layer. Bar and fuel extents are the dark
    strips of that panel image around the objects' placements."""
    at = {}
    for name, x, y, _ in placements:
        at.setdefault(name, (x, y))
    fields = ('Lives', 'Score', 'ammo', 'Fuel', 'Item Player')
    if any(f'{f} {p}' not in at for f in fields for p in (1, 2)):
        return []
    displays = {o['id']: o for g in docs['displays.json']['global_object_lists'] for o in g['objects']}
    globals_by_name = {o['name']: o['id'] for g in docs['project-index.json']['global_object_lists'] for o in g}
    def sections(name):
        data = displays.get(globals_by_name.get(name), {}).get('display_data') or []
        return data[0]['sections'] if len(data) == 1 else []
    digits = next((s['image_ids'] for s in sections('ammo 1') if s['type_raw_u16'] == 1 and len(s['image_ids'] or []) >= 10), None)
    if not digits:
        return []
    lines = []
    for player in (1, 2):
        for field, name in enumerate(fields):
            x, y = at[f'{name} {player}']
            lines.append(f'hudfield {player - 1} {field} {x} {y}')
    for n, image in enumerate(digits[:11]):
        image_info(image)
        lines.append(f'huddigit {n} {image}')
    # Item Player directions: 16 ice gun, 0 flame thrower, 8 rocket launcher, 24 empty hand.
    for weapon, direction in enumerate((24, 16, 0, 8)):
        found = sequence('Item Player 1', 0, direction)
        if found:
            lines += [f'hudweapon {weapon} {found[0]} {image}' for image in found[1]]
    fuel = next((s for s in sections('Fuel 1') if s['type_raw_u16'] == 3), None)
    panel = next(((x, y, o) for o in docs['backdrops.json']['global_object_lists'][0]['objects']
                  if o['backdrop'] and o['backdrop']['artwork']['kind'] in {'image', 'mosaic'}
                  for n, x, y, _ in placements if n == 'Scorebord' and globals_by_name.get('Scorebord') == o['id']), None)
    if panel:
        px, py, o = panel
        width, height, rgba = image_info(o['backdrop']['artwork']['image_id'])
        art = o['backdrop']['artwork']
        if art['kind'] == 'image':
            lines.append(f'hudpanel {art["image_id"]} {px} {py} {width} {height} 0')
        else:
            pw, ph = struct.unpack_from('<HH', bytes.fromhex(o['backdrop']['header_hex']), 34)
            lines.append(f'hudpanel {art["image_id"]} {px} {py} {pw} {ph} 1')
        def dark(x, y):
            x, y = x - px, y - py
            if not (0 <= x < width and 0 <= y < height):
                return False
            r, g, b = rgba[(y * width + x) * 4:(y * width + x) * 4 + 3]
            return r + g + b < 60
        if fuel:
            fx, fy = at['Fuel 1']
            run = 0
            while dark(fx + run, fy):
                run += 1
            tall = 0
            while dark(fx + 1, fy + tall):
                tall += 1
            red, green, blue = bytes.fromhex(fuel['raw_hex'])[6:9]
            if run and tall:
                lines.append(f'hudfuel {red:02x}{green:02x}{blue:02x} {run} {tall}')
        if 'Bar white' in at and all(n in globals_by_name for n in ('Bar white', 'Bar Blue', 'Bar Red')):
            bx, by = at['Bar white']
            left = bx - 1
            while dark(left - 1, by):
                left -= 1
            right = bx + 1
            while dark(right, by):
                right += 1
            if left < bx - 1 and right > bx + 1:
                for bar, name in enumerate(('Bar white', 'Bar Blue', 'Bar Red')):
                    found = sequence(name)
                    if found:
                        lines.append(f'hudbar {bar} {found[1][0]}')
                lines.append(f'hudbarbox {bx} {by} {left} {right}')
    return lines


def import_arena(bundle: Path, output: Path, frame=3):
    manifest, files, docs = checked_bundle(bundle)
    text, wanted, summary = import_lines(files, docs, frame)
    # Every other playable frame becomes an extra level beside arena.ff (the original's
    # levels are frames 3-12); title and menu frames are not arenas and are skipped.
    levels = {}
    for other in range(len(docs['project-index.json']['frames'])):
        if other == frame:
            continue
        try:
            level_text, level_wanted, _ = import_lines(files, docs, other)
        except (ValueError, KeyError, IndexError, struct.error, zlib.error):
            continue
        levels[f'level-{other}.ff'] = level_text.encode('ascii')
        wanted |= level_wanted
    summary['levels'] = sorted(int(name[6:-3]) for name in levels)
    payloads = {name: files[name] for name in sorted(wanted)}
    payloads['arena.ff'] = text.encode('ascii')
    payloads.update(levels)
    report = {'importer': 'arena-import/9', 'source_sha256': manifest['source']['sha256'], **summary,
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
        project.report_fault(type(error).__name__, version='arena-import/9', title='Arena import failed')
        print('Arena import failed; original input was not modified.', file=sys.stderr)
        return 1
    print(f'Imported frame {summary["frame"]}: {summary["layers"]} layers, {summary["spawns"]} spawn candidates, '
          f'{len(summary["levels"])} more levels.\nPlay: build/native/funny-furries --data {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
