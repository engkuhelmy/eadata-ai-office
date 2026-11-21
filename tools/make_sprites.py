#!/usr/bin/env python3
"""Jana aset sprite pixel art untuk AI Office Hub (original, gaya rujukan: kayu hangat, outline gelap).

Guna: python tools/make_sprites.py [--preview DIR]
Output: public/assets/office/*.png

Staff dipecah kepada 4 lapisan supaya boleh diwarnakan (tint) dalam Phaser:
  staff_fixed (outline, seluar, kasut, mata), staff_skin, staff_hair, staff_shirt (warna vendor).
Setiap sheet: 8 frame 32x48 dalam satu baris: 0-1 idle, 2-5 walk, 6-7 typing (duduk).
Furniture: sprite tile 56 lebar, anchor bawah-tengah = bucu bawah tile (tengah tile + 14px).
"""
import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / 'public' / 'assets' / 'office'

OL = (58, 36, 20, 255)

# ---------------------------------------------------------------- staff

FW, FH = 32, 48

FIXED = {
    'outline': {1: OL},
    'pants': {0: (46, 66, 96, 255), 1: (62, 90, 124, 255), 2: (82, 112, 148, 255)},
    'shoes': {0: (70, 42, 28, 255), 1: (104, 66, 44, 255), 2: (128, 84, 58, 255)},
    'eyes': {1: (42, 34, 28, 255)},
    'mouth': {1: (150, 70, 56, 255)},
}
TINT_LEVELS = {
    'skin': {0: 0.80, 1: 1.0, 2: 1.0},
    'hair': {0: 0.62, 1: 0.88, 2: 1.0},
    'shirt': {0: 0.68, 1: 0.90, 2: 1.0},
}


class Buf:
    def __init__(self):
        self.px = {}

    def put(self, x, y, role, shade=1):
        if 0 <= x < FW and 0 <= y < FH:
            self.px[(x, y)] = (role, shade)

    def rect(self, x0, y0, x1, y1, role, shade=1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                s = shade(x, y) if callable(shade) else shade
                self.put(x, y, role, s)


def figure(dy=0, seated=False, lx=0, rx=0, llift=0, rlift=0, al=0, ar=0, typing=None):
    b = Buf()
    y0 = 6 + dy

    # Kepala (11 lebar, 11 tinggi, bucu dibulatkan)
    for row in range(11):
        x0, x1 = (12, 20) if row in (0, 9) else (13, 19) if row == 10 else (11, 21)
        for x in range(x0, x1 + 1):
            b.put(x, y0 + row, 'skin', 0 if row >= 9 else 1)

    # Rambut: fringe, tepi dan sideburn
    for x in range(12, 21):
        b.put(x, y0, 'hair', 2)
    for row in (1, 2):
        for x in range(11, 22):
            b.put(x, y0 + row, 'hair', 1 if row == 1 else 0 if x in (11, 21) else 1)
    for x in (11, 12, 20, 21):
        b.put(x, y0 + 3, 'hair', 1)
    for x in (13, 14, 15):
        b.put(x, y0 + 3, 'hair', 2)
    b.put(11, y0 + 4, 'hair', 0)
    b.put(21, y0 + 4, 'hair', 0)

    # Muka
    b.put(14, y0 + 5, 'eyes')
    b.put(18, y0 + 5, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'mouth')

    # Leher dan badan (hoodie)
    yt = y0 + 12
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    for row in range(14):
        for x in range(11, 21):
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            if row >= 12:
                shade = 0
            b.put(x, yt + row, 'shirt', shade)
    for x in (15, 16, 17):
        b.put(x, yt, 'skin', 1)
    b.put(16, yt + 1, 'skin', 1)
    b.put(14, yt + 3, 'shirt', 2)
    b.put(18, yt + 3, 'shirt', 2)
    b.put(14, yt + 4, 'shirt', 2)
    b.put(18, yt + 4, 'shirt', 2)

    # Lengan
    if typing is None:
        for dx0, off, shades in ((7, al, (2, 1, 1)), (22, ar, (1, 1, 0))):
            for row in range(9):
                for i in range(3):
                    b.put(dx0 + i, yt + 1 + off + row, 'shirt', shades[i])
            for row in range(2):
                for i in range(3):
                    b.put(dx0 + i, yt + 10 + off + row, 'skin', 1)
    else:
        for side in (0, 1):
            raise_hand = (typing + side) % 2
            for k in range(8):
                shift = (k * 3) // 4
                xs = (8 + shift) if side == 0 else (21 - shift)
                for i in range(3):
                    b.put(xs + i - 1, yt + 1 + k, 'shirt', 2 if (side == 0 and i == 0) else 0 if (side == 1 and i == 2) else 1)
            hx = 8 + 6 if side == 0 else 21 - 6
            for i in range(2):
                for j in range(2):
                    b.put(hx + i - 1, yt + 9 - raise_hand + j, 'skin', 1)

    # Kaki dan kasut
    if not seated:
        for x0, off, lift, shades in ((11, lx, llift, (2, 1, 1, 1, 0)), (16, rx, rlift, (1, 1, 1, 1, 0))):
            bottom = 43 - lift
            for y in range(32, bottom + 1):
                for i in range(5):
                    b.put(x0 + off + i, y, 'pants', shades[i])
            for y in range(bottom + 1, bottom + 4):
                for i in range(-1 if x0 == 11 else 0, 6 if x0 == 16 else 5):
                    b.put(x0 + off + i, y, 'shoes', 0 if y == bottom + 3 else 1)

    # Outline automatik di sekeliling bentuk
    cells = set(b.px)
    for x in range(-1, FW + 1):
        for y in range(-1, FH + 1):
            if (x, y) in cells:
                continue
            if any((x + dx, y + dy_) in cells for dx, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                b.put(x, y, 'outline', 1)

    return b


def add_outline(b):
    cells = set(b.px)
    for x in range(-1, FW + 1):
        for y in range(-1, FH + 1):
            if (x, y) in cells:
                continue
            if any((x + dx, y + dy_) in cells for dx, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                b.put(x, y, 'outline', 1)
    return b


def figure_back(typing=0):
    """Duduk dari belakang, menghadap meja (macam staff dalam gambar rujukan)."""
    b = Buf()
    y0 = 10

    # Kepala dari belakang: rambut penuh, tengkuk dan telinga nampak sedikit
    for row in range(11):
        x0, x1 = (12, 20) if row in (0, 9) else (13, 19) if row == 10 else (11, 21)
        for x in range(x0, x1 + 1):
            shade = 2 if row <= 2 else 1 if row <= 6 else 0
            b.put(x, y0 + row, 'hair', shade)
    for x in (14, 15, 16, 17, 18):
        b.put(x, y0 + 10, 'skin', 0)
    for row in (5, 6):
        b.put(10, y0 + row, 'skin', 1)
        b.put(22, y0 + row, 'skin', 0)

    # Badan (belakang hoodie) dengan hood
    yt = y0 + 12
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    for row in range(14):
        for x in range(11, 21):
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            b.put(x, yt + row, 'shirt', shade)
    for x in range(13, 20):
        b.put(x, yt, 'shirt', 0)
        b.put(x, yt + 1, 'shirt', 0)
    for x in range(14, 19):
        b.put(x, yt + 2, 'shirt', 0)

    # Lengan atas di sisi, siku bergerak bila menaip
    for side, x0 in ((0, 8), (1, 21)):
        lift = (typing + side) % 2
        for row in range(7):
            for i in range(3):
                shade = (2, 1, 1)[i] if side == 0 else (1, 1, 0)[i]
                b.put(x0 + i, yt + 1 + row - lift, 'shirt', shade)

    return add_outline(b)


FRAMES = [
    dict(dy=0),
    dict(dy=1),
    dict(lx=-1, rx=1, al=1, ar=-1),
    dict(rlift=2, dy=-1),
    dict(lx=1, rx=-1, al=-1, ar=1),
    dict(llift=2, dy=-1),
    dict(dy=4, seated=True, typing=0),
    dict(dy=4, seated=True, typing=1),
    dict(back=True, typing=0),
    dict(back=True, typing=1),
]


def staff_sheets():
    sheets = {name: Image.new('RGBA', (FW * len(FRAMES), FH), (0, 0, 0, 0)) for name in ('fixed', 'skin', 'hair', 'shirt')}
    for index, pose in enumerate(FRAMES):
        buf = figure_back(pose['typing']) if pose.get('back') else figure(**pose)
        for (x, y), (role, shade) in buf.px.items():
            ox = index * FW + x
            if role in FIXED:
                sheets['fixed'].putpixel((ox, y), FIXED[role][shade] if shade in FIXED[role] else FIXED[role][1])
            else:
                level = int(255 * TINT_LEVELS[role][shade])
                sheets[role].putpixel((ox, y), (level, level, level, 255))
    return sheets


# ---------------------------------------------------------------- furniture

WOOD = dict(top=(201, 147, 93, 255), hi=(226, 176, 118, 255), left=(160, 106, 62, 255), right=(128, 80, 44, 255))


def box(d, hs, h, top, left, right, hi=None):
    cx, cy = 28, hs - 14
    d.polygon([(cx - 28, cy - h), (cx, cy - h + 14), (cx, cy + 14), (cx - 28, cy)], fill=left, outline=OL)
    d.polygon([(cx + 28, cy - h), (cx, cy - h + 14), (cx, cy + 14), (cx + 28, cy)], fill=right, outline=OL)
    d.polygon([(cx, cy - h - 14), (cx + 28, cy - h), (cx, cy - h + 14), (cx - 28, cy - h)], fill=top, outline=OL)
    if hi:
        d.line([(cx - 26, cy - h), (cx, cy - h - 12), (cx + 26, cy - h)], fill=hi)
    return cx, cy


def new(w, h):
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def desk():
    img, d = new(56, 64)
    cx, cy = box(d, 64, 14, WOOD['top'], WOOD['left'], WOOD['right'], WOOD['hi'])
    # Grain
    for dx in (-14, -4, 8):
        d.line([(cx + dx, cy - 14 + 8), (cx + dx + 10, cy - 14 + 3)], fill=(180, 126, 76, 255))
    # Laci pada muka kanan
    d.line([(cx + 4, cy - 6 + 5), (cx + 24, cy - 6 - 5)], fill=OL)
    d.rectangle([cx + 12, cy - 3, cx + 15, cy - 1], fill=(222, 176, 120, 255))
    # Monitor (skrin 10x7 pada (23,21) ditindih animasi oleh Phaser)
    d.rectangle([21, 19, 34, 31], fill=(52, 52, 60, 255), outline=OL)
    d.rectangle([23, 21, 32, 27], fill=(20, 40, 28, 255))
    d.rectangle([27, 32, 29, 34], fill=(96, 96, 104, 255))
    d.rectangle([23, 35, 33, 36], fill=(74, 74, 82, 255), outline=OL)
    # Papan kekunci, tetikus, mug, kertas
    d.rectangle([20, 39, 32, 42], fill=(190, 190, 196, 255), outline=OL)
    d.line([(21, 40), (31, 40)], fill=(150, 150, 158, 255))
    d.rectangle([36, 40, 38, 41], fill=(230, 230, 236, 255), outline=OL)
    d.rectangle([40, 33, 44, 37], fill=(240, 240, 240, 255), outline=OL)
    d.rectangle([41, 34, 43, 35], fill=(120, 72, 40, 255))
    d.polygon([(8, 36), (16, 32), (22, 35), (14, 39)], fill=(240, 236, 222, 255), outline=OL)
    return img


def chair():
    """Kerusi pejabat dilihat dari belakang. Tanah pada y=37. Sandaran rendah supaya
    kepala dan bahu staff yang duduk nampak di atasnya (macam gambar rujukan)."""
    img, d = new(32, 40)
    base = (60, 60, 68, 255)
    for end in ((5, 37), (27, 37), (10, 39), (22, 39)):
        d.line([(16, 34), end], fill=base, width=2)
    for x in (5, 27, 10, 22):
        d.point((x, 38 if x in (5, 27) else 39), fill=(30, 30, 34, 255))
    d.rectangle([15, 27, 17, 34], fill=(52, 52, 60, 255))
    d.rounded_rectangle([5, 23, 27, 28], radius=2, fill=(52, 52, 60, 255), outline=OL)
    d.rectangle([3, 20, 6, 27], fill=(44, 44, 52, 255), outline=OL)
    d.rectangle([26, 20, 29, 27], fill=(44, 44, 52, 255), outline=OL)
    d.rounded_rectangle([8, 12, 24, 25], radius=3, fill=(40, 40, 48, 255), outline=OL)
    d.line([(10, 14), (22, 14)], fill=(88, 88, 100, 255))
    d.line([(10, 15), (10, 22)], fill=(70, 70, 82, 255))
    return img


def partition():
    """Dinding separuh (partition) sepanjang paksi c, macam bilik dalam gambar rujukan.
    Tile center pada (28, 66). Flip mendatar untuk paksi r."""
    img, d = new(56, 80)
    cream, cap, base, edge = (236, 218, 184, 255), (250, 240, 220, 255), (196, 150, 98, 255), (214, 192, 156, 255)
    h = 46
    a, b = (14, 59), (42, 73)
    d.polygon([a, b, (b[0], b[1] - h), (a[0], a[1] - h)], fill=cream, outline=OL)
    d.polygon([(a[0], a[1] - 6), (b[0], b[1] - 6), b, a], fill=base, outline=OL)
    d.polygon([(a[0], a[1] - h), (b[0], b[1] - h), (b[0] + 4, b[1] - h - 2), (a[0] + 4, a[1] - h - 2)], fill=cap, outline=OL)
    d.polygon([(b[0], b[1] - h), (b[0] + 4, b[1] - h - 2), (b[0] + 4, b[1] - 2), b], fill=edge, outline=OL)
    return img


def partition_poster():
    """Partition dengan poster awan EA (tanpa teks supaya boleh di-flip)."""
    img = partition()
    d = ImageDraw.Draw(img)
    d.polygon([(20, 24), (36, 32), (36, 52), (20, 44)], fill=(250, 246, 232, 255), outline=OL)
    sky, line = (120, 190, 235, 255), (40, 90, 160, 255)
    d.polygon([(22, 33), (26, 29), (31, 31), (34, 36), (34, 41), (22, 35)], fill=sky, outline=line)
    d.line([(24, 39), (33, 43)], fill=(24, 54, 120, 255))
    return img


def plant():
    img, d = new(48, 64)
    d.polygon([(14, 46), (34, 46), (31, 60), (17, 60)], fill=(190, 96, 54, 255), outline=OL)
    d.rectangle([12, 43, 35, 47], fill=(214, 124, 76, 255), outline=OL)
    d.line([(16, 50), (30, 50)], fill=(160, 78, 44, 255))
    d.ellipse([24, 36, 24, 36], fill=OL)
    d.line([(24, 44), (24, 34)], fill=(80, 54, 30, 255), width=2)
    dark, mid, light = (44, 90, 48, 255), (68, 124, 62, 255), (104, 162, 88, 255)
    for (x, y, r) in ((24, 22, 17), (13, 32, 10), (35, 32, 10), (24, 11, 11)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=mid, outline=(34, 70, 40, 255))
    rnd = random.Random(7)
    for _ in range(46):
        x, y = rnd.randint(8, 40), rnd.randint(4, 40)
        if img.getpixel((x, y))[3]:
            col = light if rnd.random() < 0.5 else dark
            d.rectangle([x, y, x + 1, y], fill=col)
    return img


def shelf():
    img, d = new(56, 70)
    cx, cy = box(d, 70, 42, (110, 74, 42, 255), (96, 62, 34, 255), (78, 48, 26, 255), (140, 98, 58, 255))
    books = [(178, 40, 40), (40, 84, 170), (46, 128, 70), (200, 148, 36), (120, 64, 170), (200, 80, 120), (210, 110, 40)]
    rnd = random.Random(3)
    for row in range(3):
        for face in ('L', 'R'):
            xs = range(2, 26, 3) if face == 'L' else range(30, 54, 3)
            for x in xs:
                top_edge = 14 + x // 2 if face == 'L' else 28 - (x - 28) // 2
                y = top_edge + 3 + row * 13
                col = rnd.choice(books) + (255,)
                d.rectangle([x, y + rnd.randint(0, 2), x + 1, y + 9], fill=col, outline=None)
            # papan rak
            if face == 'L':
                d.line([(1, 14 + 12 + row * 13 + 1), (27, 28 + 12 + row * 13 - 1)], fill=OL)
            else:
                d.line([(29, 28 + 12 + row * 13 - 1), (55, 14 + 12 + row * 13 + 1)], fill=OL)
    return img


def cooler():
    img, d = new(56, 70)
    cx, cy = box(d, 70, 22, (236, 240, 244, 255), (186, 196, 208, 255), (150, 164, 182, 255), (255, 255, 255, 255))
    d.rectangle([18, cy - 10, 21, cy - 6], fill=(220, 60, 60, 255))
    d.rectangle([18, cy - 4, 21, cy], fill=(60, 120, 220, 255))
    d.rectangle([20, cy - 26 - 6, 36, cy - 22 - 1], fill=(140, 200, 240, 255), outline=OL)
    d.ellipse([20, cy - 26 - 10, 36, cy - 26 - 2], fill=(190, 226, 250, 255), outline=OL)
    d.line([(24, cy - 28), (24, cy - 24)], fill=(255, 255, 255, 255))
    return img


def sofa():
    img, d = new(56, 58)
    cx, cy = 28, 58 - 14
    red, red_l, red_r, red_t = (196, 72, 44, 255), (150, 50, 30, 255), (120, 38, 22, 255), (214, 96, 60, 255)
    d.polygon([(cx - 28, cy - 12), (cx, cy - 12 - 14), (cx, cy - 12 - 14 - 16), (cx - 28, cy - 12 - 16)], fill=red_l, outline=OL)
    d.polygon([(cx, cy - 12 - 14), (cx + 28, cy - 12), (cx + 28, cy - 12 - 16), (cx, cy - 12 - 14 - 16)], fill=red_r, outline=OL)
    box(d, 58, 12, red_t, red_l, red_r, (232, 130, 90, 255))
    d.line([(cx, cy - 12 - 14), (cx, cy - 12 + 14)], fill=(150, 50, 30, 255))
    return img


def machine():
    img, d = new(56, 68)
    cx, cy = box(d, 68, 18, (140, 98, 62, 255), (100, 66, 40, 255), (78, 50, 30, 255), (170, 124, 82, 255))
    d.rectangle([14, cy - 18 - 24, 30, cy - 18 - 2], fill=(54, 54, 62, 255), outline=OL)
    d.rectangle([17, cy - 18 - 20, 27, cy - 18 - 14], fill=(30, 30, 36, 255))
    d.rectangle([24, cy - 18 - 12, 25, cy - 18 - 11], fill=(230, 60, 60, 255))
    d.rectangle([32, cy - 18 - 12, 38, cy - 18 - 2], fill=(210, 230, 240, 255), outline=OL)
    d.rectangle([33, cy - 18 - 8, 37, cy - 18 - 3], fill=(96, 56, 30, 255))
    d.rectangle([42, cy - 18 - 6, 45, cy - 18 - 2], fill=(244, 244, 244, 255), outline=OL)
    return img


def server():
    img, d = new(56, 72)
    cx, cy = box(d, 72, 44, (74, 86, 94, 255), (50, 62, 70, 255), (38, 48, 54, 255), (110, 124, 134, 255))
    for k in range(7):
        y = 20 + k * 6
        d.line([(2, 14 + y - 20 + 4 + 1), (26, 28 + y - 20 + 4 - 1)], fill=(26, 34, 40, 255))
        d.line([(30, 28 + y - 20 + 4 - 1), (54, 14 + y - 20 + 4 + 1)], fill=(60, 74, 82, 255))
    return img


def pong():
    img, d = new(56, 42)
    cx, cy = box(d, 42, 6, (48, 130, 70, 255), (30, 90, 48, 255), (22, 70, 38, 255))
    d.polygon([(cx, cy - 6 - 11), (cx + 22, cy - 6), (cx, cy - 6 + 11), (cx - 22, cy - 6)], outline=(240, 240, 240, 255))
    d.line([(cx - 11, cy - 6 - 6), (cx + 11, cy - 6 + 6)], fill=(240, 240, 240, 255))
    d.line([(cx - 12, cy - 6 - 6), (cx - 12, cy - 6 - 11)], fill=(200, 200, 210, 255))
    d.line([(cx + 10, cy - 6 + 6), (cx + 10, cy - 6 + 1)], fill=(200, 200, 210, 255))
    return img


def foos():
    img, d = new(56, 46)
    cx, cy = box(d, 46, 10, (40, 120, 190, 255), (28, 84, 140, 255), (20, 62, 108, 255), (90, 160, 220, 255))
    for k in range(-2, 3):
        d.line([(cx + k * 4 - 8, cy - 10 + k * 2 + 6), (cx + k * 4 + 8, cy - 10 + k * 2 - 2)], fill=(200, 200, 210, 255))
    for k in range(-2, 3):
        d.rectangle([cx + k * 4, cy - 10 + k * 2 + 2, cx + k * 4 + 1, cy - 10 + k * 2 + 3], fill=(220, 60, 50, 255))
    return img


def table():
    img, d = new(56, 52)
    cx, cy = box(d, 52, 10, (176, 128, 80, 255), (130, 88, 52, 255), (104, 68, 38, 255), (206, 160, 106, 255))
    d.polygon([(cx - 10, cy - 10), (cx, cy - 15), (cx + 8, cy - 11), (cx - 2, cy - 6)], fill=(236, 232, 218, 255), outline=OL)
    d.rectangle([cx + 6, cy - 22, cx + 14, cy - 15], fill=(60, 60, 70, 255), outline=OL)
    d.polygon([(cx + 4, cy - 10), (cx + 13, cy - 8), (cx + 8, cy - 4), (cx - 1, cy - 6)], fill=(110, 190, 150, 255), outline=OL)
    return img


def reception():
    img, d = new(56, 58)
    cx, cy = box(d, 58, 16, (186, 130, 78, 255), (140, 90, 52, 255), (112, 70, 38, 255), (218, 166, 108, 255))
    d.rectangle([cx + 6, cy - 12, cx + 20, cy - 3], fill=(250, 246, 232, 255), outline=OL)
    d.line([(cx + 8, cy - 8), (cx + 17, cy - 8)], fill=(90, 150, 200, 255))
    d.rectangle([cx - 12, cy - 16 - 12, cx - 2, cy - 16 - 4], fill=(52, 52, 60, 255), outline=OL)
    d.rectangle([cx - 10, cy - 16 - 10, cx - 4, cy - 16 - 6], fill=(60, 140, 200, 255))
    return img


def bell():
    img, d = new(56, 52)
    cx, cy = box(d, 52, 16, (226, 190, 100, 255), (178, 142, 62, 255), (146, 112, 46, 255), (246, 220, 140, 255))
    d.ellipse([cx - 7, cy - 16 - 14, cx + 7, cy - 16 + 1], fill=(250, 204, 21, 255), outline=OL)
    d.rectangle([cx - 1, cy - 16 - 17, cx + 1, cy - 16 - 14], fill=OL)
    return img


def floor_tile(base, seed):
    img, d = new(56, 28)
    pts = [(28, 0), (55, 14), (28, 27), (0, 14)]
    d.polygon(pts, fill=base)
    rnd = random.Random(seed)
    for _ in range(26):
        x, y = rnd.randint(6, 50), rnd.randint(4, 24)
        if img.getpixel((x, y))[3]:
            shift = rnd.choice((-14, -8, 8, 12))
            col = tuple(max(0, min(255, c + shift)) for c in base[:3]) + (255,)
            d.line([(x, y), (x + rnd.randint(1, 4), y)], fill=col)
    d.polygon(pts, outline=(150, 100, 56, 255))
    return img


# ---------------------------------------------------------------- dinding
# Lukis rata dulu, kemudian di-shear supaya selari dengan dinding isometric.
# 'A' condong turun ke kanan, 'B' condong turun ke kiri (1px y setiap 2px x).

def shear(img, wall):
    w, h = img.size
    size = (w, h + w // 2)
    if wall == 'A':
        return img.transform(size, Image.AFFINE, (1, 0, 0, -0.5, 1, 0), resample=Image.NEAREST)
    return img.transform(size, Image.AFFINE, (1, 0, 0, 0.5, 1, -0.5 * w), resample=Image.NEAREST)


def pixel_text(img, xy, text, size, fill):
    """Teks tanpa anti-alias supaya kekal pixel art."""
    from PIL import ImageFont
    font = ImageFont.load_default(size=size)
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255)
    mask = mask.point(lambda v: 255 if v > 110 else 0)
    img.paste(Image.new('RGBA', img.size, fill), (0, 0), mask)


def wall_window():
    img, d = new(45, 58)
    d.rectangle([0, 0, 44, 57], fill=(124, 80, 46, 255), outline=OL)
    for y in range(3, 52):
        t = (y - 3) / 48
        col = (255, int(214 + 30 * t), int(128 + 70 * t), 255)
        d.line([(3, y), (41, y)], fill=col)
    for y in range(5, 30, 4):
        d.line([(3, y), (41, y)], fill=(224, 172, 96, 255))
    d.rectangle([21, 3, 23, 51], fill=(124, 80, 46, 255))
    d.rectangle([3, 30, 41, 32], fill=(124, 80, 46, 255))
    d.rectangle([0, 52, 44, 57], fill=(150, 98, 56, 255), outline=OL)
    d.line([(4, 5), (14, 5)], fill=(255, 250, 220, 255))
    return img


def wall_board():
    img, d = new(73, 58)
    d.rectangle([0, 0, 72, 57], fill=(190, 122, 72, 255), outline=OL)
    d.rectangle([3, 3, 69, 49], fill=(248, 250, 252, 255), outline=(150, 120, 90, 255))
    d.rectangle([3, 51, 69, 55], fill=(150, 96, 56, 255))
    pts = [(8, 38), (18, 32), (28, 35), (40, 22), (52, 26), (64, 12)]
    d.line(pts, fill=(34, 160, 90, 255), width=2)
    for i, (x, h, col) in enumerate(((10, 10, (230, 130, 60)), (16, 16, (60, 120, 200)), (22, 12, (230, 130, 60)))):
        d.rectangle([x + 40 + i * 0, 46 - h, x + 44, 46], fill=col + (255,))
    for y in (8, 12):
        d.line([(8, y), (30 + y, y)], fill=(160, 170, 180, 255))
    d.rectangle([46, 8, 55, 15], fill=(253, 230, 138, 255), outline=OL)
    d.rectangle([58, 8, 67, 15], fill=(251, 207, 232, 255), outline=OL)
    return img


def wall_cork():
    img, d = new(82, 56)
    d.rectangle([0, 0, 81, 55], fill=(200, 160, 100, 255), outline=OL)
    d.rectangle([3, 3, 78, 52], fill=(206, 166, 108, 255))
    rnd = random.Random(11)
    for _ in range(70):
        x, y = rnd.randint(4, 77), rnd.randint(4, 51)
        d.point((x, y), fill=(176, 136, 84, 255))
    colors = [(253, 230, 138), (252, 165, 165), (147, 197, 253), (187, 247, 208), (251, 207, 232), (255, 255, 255)]
    spots = [(6, 6), (22, 8), (38, 5), (54, 9), (66, 6), (8, 28), (24, 30), (40, 27), (56, 31), (68, 28), (14, 40), (48, 41)]
    for i, (x, y) in enumerate(spots):
        c = colors[i % len(colors)]
        d.rectangle([x, y, x + 9, y + 9], fill=c + (255,), outline=(120, 90, 60, 255))
        d.line([(x + 2, y + 3), (x + 7, y + 3)], fill=(120, 110, 100, 255))
        d.line([(x + 2, y + 6), (x + 6, y + 6)], fill=(120, 110, 100, 255))
        d.point((x + 4, y), fill=(220, 40, 40, 255))
    return img


def wall_poster(kind):
    img, d = new(28, 40)
    d.rectangle([0, 0, 27, 39], fill=(250, 244, 226, 255), outline=OL)
    if kind == 'sun':
        d.rectangle([3, 3, 24, 36], fill=(70, 120, 190, 255))
        d.ellipse([8, 9, 19, 20], fill=(250, 204, 21, 255), outline=OL)
        d.polygon([(3, 36), (10, 26), (16, 32), (24, 24), (24, 36)], fill=(60, 140, 90, 255))
    else:
        d.rectangle([3, 3, 24, 36], fill=(252, 246, 230, 255), outline=(150, 120, 90, 255))
        for i, h in enumerate((8, 14, 11, 20)):
            d.rectangle([6 + i * 5, 33 - h, 9 + i * 5, 33], fill=((230, 130, 60), (60, 120, 200), (46, 160, 90), (200, 70, 90))[i] + (255,))
        d.line([(6, 8), (21, 8)], fill=(150, 150, 160, 255))
    return img


def wall_logo():
    """Logo awan "EA Clouds Technology" gaya pixel art (jenama pengguna)."""
    img, d = new(64, 44)
    d.rounded_rectangle([0, 0, 63, 43], radius=3, fill=(250, 244, 226, 255), outline=OL)
    sky = (120, 190, 235, 255)
    for (x, y, r) in ((20, 22, 9), (32, 17, 12), (44, 22, 9), (28, 26, 9), (38, 26, 9)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=sky, outline=(40, 90, 160, 255))
    d.rectangle([18, 20, 46, 32], fill=sky)
    d.line([(14, 33), (50, 33)], fill=(40, 90, 160, 255))
    for dx in (0, 1):
        pixel_text(img, (19 + dx, 9), 'EA', 20, (24, 54, 120, 255))
    pixel_text(img, (14, 34), 'Clouds', 8, (24, 54, 120, 255))
    return img


def build(preview=None):
    OUT.mkdir(parents=True, exist_ok=True)

    walls = {
        'wall_window_a': shear(wall_window(), 'A'), 'wall_window_b': shear(wall_window(), 'B'),
        'wall_board_a': shear(wall_board(), 'A'), 'wall_cork_b': shear(wall_cork(), 'B'),
        'wall_poster_a1': shear(wall_poster('chart'), 'A'), 'wall_poster_a2': shear(wall_poster('sun'), 'A'),
        'wall_poster_b': shear(wall_poster('sun'), 'B'), 'wall_logo_b': shear(wall_logo(), 'B'),
        'brand_logo': wall_logo(),
        'partition_a': partition(), 'partition_b': partition().transpose(Image.FLIP_LEFT_RIGHT),
        'partition_a_logo': partition_poster(), 'partition_b_logo': partition_poster().transpose(Image.FLIP_LEFT_RIGHT),
    }
    for name, img in walls.items():
        img.save(OUT / f'{name}.png')

    for name, sheet in staff_sheets().items():
        sheet.save(OUT / f'staff_{name}.png')

    assets = {
        'desk': desk(), 'chair': chair(), 'plant': plant(), 'shelf': shelf(), 'cooler': cooler(),
        'sofa': sofa(), 'machine': machine(), 'server': server(), 'pong': pong(), 'foos': foos(),
        'table': table(), 'reception': reception(), 'bell': bell(),
        'floor_a': floor_tile((234, 180, 114, 255), 1), 'floor_b': floor_tile((206, 142, 82, 255), 2),
    }
    for name, img in assets.items():
        img.save(OUT / f'{name}.png')

    print(f'{len(assets) + 4} fail ditulis ke {OUT}')

    if preview:
        make_preview(Path(preview), assets)


def make_preview(folder, assets):
    folder.mkdir(parents=True, exist_ok=True)
    sheets = {n: Image.open(OUT / f'staff_{n}.png') for n in ('fixed', 'skin', 'hair', 'shirt')}

    def tint(img, color):
        px = img.load()
        out = img.copy()
        o = out.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if a:
                    o[x, y] = (r * color[0] // 255, g * color[1] // 255, b * color[2] // 255, a)
        return out

    combos = [((217, 119, 87), (242, 207, 174), (42, 34, 25)), ((16, 163, 127), (141, 85, 36), (109, 76, 42)),
              ((139, 92, 246), (217, 165, 119), (31, 41, 55)), ((100, 116, 139), (245, 208, 176), (161, 98, 7))]
    staff = Image.new('RGBA', (FW * len(FRAMES), FH * len(combos)), (200, 160, 110, 255))
    for row, (shirt, skin, hair) in enumerate(combos):
        for layer, color in (('skin', skin), ('hair', hair), ('shirt', shirt)):
            staff.alpha_composite(tint(sheets[layer], color), (0, row * FH))
        staff.alpha_composite(sheets['fixed'], (0, row * FH))
    staff.resize((staff.width * 4, staff.height * 4), Image.NEAREST).save(folder / 'preview_staff.png')

    names = list(assets)
    cols = 5
    cell_w, cell_h = 120, 110
    sheet = Image.new('RGBA', (cols * cell_w, ((len(names) + cols - 1) // cols) * cell_h), (190, 140, 90, 255))
    for i, name in enumerate(names):
        img = assets[name]
        sheet.alpha_composite(img, ((i % cols) * cell_w + (cell_w - img.width) // 2, (i // cols) * cell_h + cell_h - img.height - 4))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(folder / 'preview_furniture.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', help='folder untuk preview PNG')
    build(parser.parse_args().preview)
