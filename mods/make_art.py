#!/usr/bin/env python3
"""Draw the art of the example mods. Everything here is our own work (CC0-1.0);
nothing comes from the original game. Needs Pillow; the PNGs are committed, so
players and modders never run this."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def outline(image, colour=(24, 34, 62, 255)):
    """One-pixel dark outline around every opaque pixel, like the original sprites."""
    alpha = image.getchannel('A').point(lambda a: 255 if a > 100 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(3))
    edge = Image.new('RGBA', image.size, colour)
    base = Image.new('RGBA', image.size, (0, 0, 0, 0))
    base.paste(edge, mask=grown)
    base.alpha_composite(image)
    return base


def ball(draw, cx, cy, r, light=(255, 255, 255), shade=(170, 200, 235)):
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            d = math.hypot(x, y)
            if d <= r + 0.3:
                t = max(0.0, min(1.0, (x + y) / (2 * r) + 0.35))
                c = tuple(int(light[i] * (1 - t) + shade[i] * t) for i in range(3))
                draw.point((cx + x, cy + y), fill=c + (255,))
    draw.point((cx - r // 2, cy - r // 2), fill=(255, 255, 255, 255))


# ---------------------------------------------------------------- snowball arsenal
def arsenal(root):
    # Snowball shot.
    im = Image.new('RGBA', (11, 11), (0, 0, 0, 0))
    ball(ImageDraw.Draw(im), 5, 5, 4)
    save(outline(im), root / 'snowball.png')
    # Pile of snowballs in a little wooden crate.
    im = Image.new('RGBA', (28, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((3, 14, 24, 22), fill=(150, 92, 48, 255))
    for x in range(3, 25, 5):
        d.line((x, 14, x, 22), fill=(118, 70, 36, 255))
    d.line((3, 14, 24, 14), fill=(196, 132, 74, 255))
    for cx, cy in ((8, 11), (14, 11), (20, 11), (11, 6), (17, 6)):
        ball(d, cx, cy, 3)
    save(outline(im), root / 'snowball-crate.png')
    # Snow cannon in the hand: a frosty blue tube with a snowball at the mouth.
    im = Image.new('RGBA', (22, 9), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(3, 19):
        t = x / 19
        d.line((x, 1, x, 7), fill=(int(70 + 60 * t), int(140 + 60 * t), 230, 255))
    d.line((3, 2, 18, 2), fill=(210, 235, 255, 255))
    d.rectangle((0, 3, 4, 8), fill=(60, 66, 90, 255))
    ball(d, 19, 4, 2)
    save(outline(im), root / 'snow-cannon.png')

    # Candy cane bolt: red and white stripes with a soft glow.
    im = Image.new('RGBA', (20, 7), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(1, 19):
        red = ((x // 3) % 2) == 0
        d.line((x, 2, x, 4), fill=(235, 40, 60, 255) if red else (255, 250, 250, 255))
    glow = im.filter(ImageFilter.GaussianBlur(1.2))
    glow.putalpha(glow.getchannel('A').point(lambda a: a // 2))
    glow.alpha_composite(im)
    save(glow, root / 'cane-bolt.png')
    # Candy cane pickup: a hooked cane with diagonal stripes.
    im = Image.new('RGBA', (18, 28), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    path = [(6, 26 - i) for i in range(18)] + [(6 + 5 - 5 * math.cos(a), 8 - 5 * math.sin(a))
                                                 for a in [i * math.pi / 14 for i in range(15)]]
    for i, (x, y) in enumerate(path):
        colour = (235, 40, 60, 255) if (i // 3) % 2 == 0 else (255, 250, 250, 255)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=colour)
    save(outline(im), root / 'candy-cane.png')
    # Candy cane rifle in the hand.
    im = Image.new('RGBA', (24, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(2, 23):
        d.line((x, 2, x, 5), fill=(235, 40, 60, 255) if (x // 3) % 2 == 0 else (255, 250, 250, 255))
    d.rectangle((0, 4, 5, 7), fill=(90, 50, 30, 255))
    save(outline(im), root / 'cane-rifle.png')

    # Gift bomb: green present, red ribbon, a lit fuse.
    def present(w, h, fuse):
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        top = 4 if fuse else 3
        d.rectangle((1, top, w - 2, h - 2), fill=(40, 160, 80, 255))
        d.line((1, top, w - 2, top), fill=(110, 220, 140, 255))
        d.rectangle((w // 2 - 1, top, w // 2, h - 2), fill=(225, 40, 50, 255))
        d.rectangle((1, (top + h) // 2, w - 2, (top + h) // 2 + 1), fill=(225, 40, 50, 255))
        d.polygon([(w // 2, top), (w // 2 - 4, top - 3), (w // 2 - 3, top)], fill=(240, 70, 80, 255))
        d.polygon([(w // 2, top), (w // 2 + 4, top - 3), (w // 2 + 3, top)], fill=(240, 70, 80, 255))
        if fuse:
            d.point((w // 2 + 2, 0), fill=(255, 230, 90, 255))
            d.point((w // 2 + 1, 1), fill=(255, 140, 40, 255))
        return outline(im)
    save(present(13, 13, True), root / 'gift-bomb.png')
    big = present(20, 19, False)
    sparkle = ImageDraw.Draw(big)
    for x, y in ((1, 2), (18, 5)):
        sparkle.point((x, y), fill=(255, 245, 160, 255))
    save(big, root / 'gift-crate.png')
    save(present(12, 11, False), root / 'gift-held.png')


# ---------------------------------------------------------------- midnight peaks
W, H = 800, 560
# One-way ledges (x0, x1, top) and solid blocks (x0, y0, x1, y1).
LEDGES = [(40, 220, 430), (580, 760, 430), (300, 500, 360), (90, 260, 280), (540, 710, 280),
          (320, 480, 190), (24, 140, 160), (660, 776, 160)]
BLOCKS = [(0, 520, 350, 560), (450, 520, 800, 560), (196, 476, 240, 520), (560, 476, 604, 520)]


def mountains(d, rng, base, height, colour, snow, step):
    points = [(0, H)]
    x, y = 0, base
    peaks = []
    while x <= W + step:
        y = max(base - height, min(base, y + rng.randint(-height // 3, height // 3)))
        points.append((x, y))
        peaks.append((x, y))
        x += step
    points.append((W, H))
    d.polygon(points, fill=colour)
    if snow:
        # A cap on every peak that stands out: a third of the way down both slopes.
        for (xa, ya), (x0, y0), (xb, yb) in zip(peaks, peaks[1:], peaks[2:]):
            if y0 < ya and y0 < yb and y0 < base - height * 0.5:
                l = (x0 + (xa - x0) * 0.35, y0 + (ya - y0) * 0.35)
                r = (x0 + (xb - x0) * 0.35, y0 + (yb - y0) * 0.35)
                mid = ((l[0] + x0) / 2, max(l[1], r[1]) - 3)
                mid2 = ((r[0] + x0) / 2, max(l[1], r[1]) + 1)
                d.polygon([(x0, y0), r, mid2, (x0, y0 + (r[1] - y0) * 0.6), mid, l], fill=snow)


def sky(path):
    rng = random.Random(1999)
    im = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=(int(6 + 30 * t), int(10 + 34 * t), int(34 + 70 * t), 255))
    for _ in range(260):
        x, y = rng.randrange(W), rng.randrange(int(H * 0.7))
        b = rng.randint(120, 255)
        d.point((x, y), fill=(b, b, min(255, b + 20), 255))
        if b > 235:
            d.point((x + 1, y), fill=(b // 2, b // 2, b // 2, 255))
            d.point((x - 1, y), fill=(b // 2, b // 2, b // 2, 255))
    # Aurora: translucent green-teal curtains following a slow wave.
    aurora = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a = ImageDraw.Draw(aurora)
    for band, (colour, phase, top) in enumerate((((60, 255, 170), 0.0, 60), ((80, 200, 255), 1.7, 95), ((170, 110, 255), 3.1, 40))):
        for x in range(W):
            y = top + 30 * math.sin(x / 90 + phase) + 12 * math.sin(x / 23 + phase * 2)
            length = 90 + 40 * math.sin(x / 57 + phase)
            for k in range(int(length)):
                alpha = int(70 * (1 - k / length) * (0.6 + 0.4 * math.sin(x / 11 + band)))
                if alpha > 0:
                    a.point((x, int(y + k)), fill=colour + (alpha,))
    im.alpha_composite(aurora.filter(ImageFilter.GaussianBlur(2)))
    # Moon with a halo.
    halo = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((600, 40, 720, 160), fill=(200, 220, 255, 60))
    im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(14)))
    d.ellipse((630, 70, 690, 130), fill=(240, 244, 255, 255))
    for cx, cy, r in ((648, 92, 6), (668, 110, 4), (672, 86, 3)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(214, 222, 240, 255))
    mountains(d, rng, 430, 170, (28, 40, 86, 255), (120, 140, 190, 255), 60)
    mountains(d, rng, 480, 150, (18, 26, 58, 255), (190, 205, 240, 255), 45)
    save(im, path)


def ledge_art(d, x0, x1, top):
    d.rounded_rectangle((x0, top, x1, top + 13), 5, fill=(96, 150, 210, 255))
    d.rectangle((x0 + 2, top + 7, x1 - 2, top + 12), fill=(66, 110, 176, 255))
    d.rounded_rectangle((x0 - 2, top - 3, x1 + 2, top + 4), 4, fill=(244, 248, 255, 255))
    for x in range(x0 + 6, x1 - 4, 9):
        length = 4 + (x * 7) % 9
        d.polygon([(x - 2, top + 13), (x + 2, top + 13), (x, top + 13 + length)], fill=(180, 220, 255, 255))


def pine(d, x, base, size):
    d.rectangle((x - 2, base - size // 4, x + 2, base), fill=(60, 40, 30, 255))
    for k in range(3):
        y = base - size // 4 - k * size // 4
        w = size // 2 - k * size // 7
        d.polygon([(x - w, y), (x + w, y), (x, y - size // 2)], fill=(20, 70, 60, 255))
        d.polygon([(x - w + 3, y - 2), (x + w - 3, y - 2), (x, y - size // 3)], fill=(235, 245, 255, 255))
        d.polygon([(x - w + 5, y - 4), (x + w - 5, y - 4), (x, y - size // 2 + 2)], fill=(20, 70, 60, 255))


def terrain(path, collision_path):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = Image.new('RGBA', (W, H), (255, 255, 255, 0))
    c = ImageDraw.Draw(col)
    for x0, y0, x1, y1 in BLOCKS:
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(46, 70, 120, 255))
        for y in range(y0 + 6, y1, 12):
            off = 0 if (y // 12) % 2 else 10
            for x in range(x0 + off, x1, 20):
                d.rectangle((x + 1, y, x + 18, y + 9), fill=(64, 94, 150, 255))
                d.line((x + 1, y, x + 18, y), fill=(98, 132, 190, 255))
        d.rounded_rectangle((x0 - 1, y0 - 5, x1, y0 + 4), 4, fill=(244, 248, 255, 255))
        c.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(0, 0, 0, 255))
    # The frozen pit: dark water far below, glowing ice at its edges.
    d.rectangle((350, 540, 449, 559), fill=(10, 30, 60, 255))
    for x in range(350, 450, 6):
        d.line((x, 548 + (x % 5), x + 4, 548 + (x % 5)), fill=(70, 160, 230, 255))
    for x0, x1, top in LEDGES:
        ledge_art(d, x0, x1, top)
        c.rectangle((x0, top, x1, top + 2), fill=(0, 0, 255, 255))
    for x, base, size in ((60, 520, 70), (300, 520, 54), (520, 520, 60), (760, 520, 76), (110, 280, 40), (690, 280, 40)):
        pine(d, x, base, size)
    save(im, path)
    save(col, collision_path)


def midnight(root):
    sky(root / 'sky.png')
    terrain(root / 'terrain.png', root / 'collision.png')


def main():
    arsenal(HERE / 'snowball-arsenal')
    midnight(HERE / 'midnight-peaks')


if __name__ == '__main__':
    main()
