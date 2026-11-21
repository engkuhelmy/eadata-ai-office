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
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / 'public' / 'assets' / 'office'

OL = (58, 36, 20, 255)

# ---------------------------------------------------------------- staff

FW, FH = 32, 48

# Gaya staff: default (asal), woman, hiphop, genz. Nama fail: default = staff_*.png (legacy).
STYLES = ('default', 'woman', 'hiphop', 'genz')
SHEET_PREFIX = {'default': 'staff', 'woman': 'staff_woman', 'hiphop': 'staff_hiphop', 'genz': 'staff_genz'}

FIXED = {
    'outline': {1: OL},
    'pants': {0: (46, 66, 96, 255), 1: (62, 90, 124, 255), 2: (82, 112, 148, 255)},
    'shoes': {0: (70, 42, 28, 255), 1: (104, 66, 44, 255), 2: (128, 84, 58, 255)},
    'eyes': {1: (42, 34, 28, 255)},
    'mouth': {1: (150, 70, 56, 255)},
    # --- role baru (gaya woman / hiphop / genz) ---
    'lips': {1: (214, 96, 112, 255)},                                           # bibir merah jambu (woman)
    'skirt': {0: (34, 40, 66, 255), 1: (50, 58, 90, 255), 2: (72, 82, 116, 255)},  # skirt navy
    'cap': {0: (18, 18, 22, 255), 1: (36, 36, 42, 255), 2: (76, 76, 88, 255),      # kap hitam, 3-4 = brim merah
            3: (226, 58, 48, 255), 4: (148, 30, 30, 255)},
    'pants2': {0: (32, 34, 40, 255), 1: (50, 53, 62, 255), 2: (74, 78, 90, 255)},  # seluar baggy arang
    'sneakers': {0: (142, 146, 156, 255), 1: (234, 236, 240, 255), 2: (255, 255, 255, 255)},  # 0 = tapak kelabu
    'gold': {1: (250, 198, 40, 255), 2: (255, 233, 130, 255)},
    'phones': {0: (150, 156, 170, 255), 1: (212, 216, 226, 255), 2: (255, 255, 255, 255)},
    'cup': {0: (186, 190, 198, 255), 1: (226, 228, 234, 255), 2: (255, 255, 255, 255)},
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


def add_outline(b):
    cells = set(b.px)
    for x in range(-1, FW + 1):
        for y in range(-1, FH + 1):
            if (x, y) in cells:
                continue
            if any((x + dx, y + dy_) in cells for dx, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                b.put(x, y, 'outline', 1)
    return b


def head_shape(b, y0, jaw_dark=True):
    """Kepala 11 lebar x 11 tinggi, bucu dibulatkan."""
    for row in range(11):
        x0, x1 = (12, 20) if row in (0, 9) else (13, 19) if row == 10 else (11, 21)
        for x in range(x0, x1 + 1):
            b.put(x, y0 + row, 'skin', 0 if (row >= 9 and jaw_dark) else 1)


def stroke(b, p0, p1, w, role, shades):
    """Garis tebal w piksel dari p0 ke p1 (untuk lengan bengkok). shades = shade ikut lebar."""
    (x0, y0), (x1, y1) = p0, p1
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    horiz = abs(x1 - x0) > abs(y1 - y0)
    for s in range(n + 1):
        cx = x0 + int(math.floor((x1 - x0) * s / n + 0.5))
        cy = y0 + int(math.floor((y1 - y0) * s / n + 0.5))
        for i in range(w):
            sh = shades[min(i, len(shades) - 1)]
            if horiz:
                b.put(cx, cy - w // 2 + i, role, sh)
            else:
                b.put(cx - w // 2 + i, cy, role, sh)


# ---- kepala (depan) ---------------------------------------------------------

def head_default(b, y0):
    head_shape(b, y0)
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


def head_woman(b, y0):
    head_shape(b, y0, jaw_dark=False)
    # Rambut panjang: volum atas lebih lebar dari kepala, jatuh ke sisi muka
    for x in range(12, 21):
        b.put(x, y0, 'hair', 2)
    for row in (1, 2):
        for x in range(10, 23):
            b.put(x, y0 + row, 'hair', 2 if (row == 1 and 12 <= x <= 16) else 0 if x in (10, 22) else 1)
    # Bangs senget ke kiri
    for x in range(11, 18):
        b.put(x, y0 + 3, 'hair', 2 if x <= 13 else 1)
    for x in (20, 21):
        b.put(x, y0 + 3, 'hair', 1)
    for x in (10, 11, 12, 20, 21, 22):
        b.put(x, y0 + 4, 'hair', 0 if x in (10, 22) else 1)
    # Rambut sisi (kiri terang, kanan gelap)
    for row in range(5, 11):
        for x, sh in ((10, 0), (11, 1), (12, 2), (20, 2), (21, 1), (22, 0)):
            if row == 10 and x in (11, 21):
                continue
            b.put(x, y0 + row, 'hair', sh)
    # Muka: bulu mata + bibir
    for x in (13, 14, 18, 19):
        b.put(x, y0 + 5, 'eyes')
    b.put(12, y0 + 4, 'eyes')
    b.put(20, y0 + 4, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'lips')


def head_hiphop(b, y0):
    head_shape(b, y0)
    # Kap snapback hitam
    for x in range(12, 21):
        b.put(x, y0, 'cap', 1)
    for row in (1, 2):
        for x in range(11, 22):
            b.put(x, y0 + row, 'cap', 2 if (row == 1 and x in (13, 14)) else 0 if x in (11, 21) else 1)
    b.put(16, y0, 'cap', 2)
    # Brim merah di atas dahi (lebih lebar dari kepala) + bayang bawah brim
    for x in range(9, 24):
        b.put(x, y0 + 3, 'cap', 3)
    for x in range(11, 22):
        b.put(x, y0 + 4, 'cap', 4)
    for y in (4, 5):
        b.put(11, y0 + y, 'hair', 0)
        b.put(21, y0 + y, 'hair', 0)
    b.put(14, y0 + 5, 'eyes')
    b.put(18, y0 + 5, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'mouth')
    b.put(16, y0 + 9, 'hair', 0)  # goatee kecil


def phones(b, y0):
    """Headphone over-ear: band di atas rambut + cawan putih di telinga."""
    for x in range(12, 21):
        b.put(x, y0 - 3, 'phones', 2 if 14 <= x <= 17 else 1)
    for x in (10, 11, 21, 22):
        b.put(x, y0 - 2, 'phones', 1)
    for row in range(-1, 3):
        b.put(9, y0 + row, 'phones', 1)
        b.put(23, y0 + row, 'phones', 1)
    for (cx0, cx1, outer) in ((8, 10, 8), (22, 24, 24)):
        for row in range(3, 8):
            for x in range(cx0, cx1 + 1):
                if row in (3, 7) and x == outer:
                    continue  # bucu dibulatkan
                b.put(x, y0 + row, 'phones', 1 if x == outer else 2)
        b.put((cx0 + cx1) // 2, y0 + 5, 'phones', 0)


def head_genz(b, y0):
    head_shape(b, y0, jaw_dark=False)
    # Rambut berdawai volum (dye): puncak tinggi, fringe senget, sisi undercut
    for x in range(12, 21):
        b.put(x, y0 - 2, 'hair', 2 if x <= 15 else 1)
    for row in (-1, 0, 1, 2):
        for x in range(10, 23):
            sh = 2 if (row in (-1, 0) and 12 <= x <= 15) else 0 if (x in (10, 22) or (row == 2 and x in (11, 21))) else 1
            b.put(x, y0 + row, 'hair', sh)
    for x in range(11, 18):
        b.put(x, y0 + 3, 'hair', 2 if x <= 13 else 1)
    for x in range(11, 15):
        b.put(x, y0 + 4, 'hair', 1)
    for row in range(3, 7):  # undercut (sisi dicukur)
        b.put(21, y0 + row, 'hair', 0)
        if row >= 5:
            b.put(11, y0 + row, 'hair', 0)
    phones(b, y0)
    b.put(14, y0 + 5, 'eyes')
    b.put(18, y0 + 5, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'mouth')


HEAD = {'default': head_default, 'woman': head_woman, 'hiphop': head_hiphop, 'genz': head_genz}


# ---- badan (depan) ------------------------------------------------------------

def torso_default(b, yt, seated):
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


def torso_woman(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    # Atasan ketat: bahu/dada lebar, pinggang kecil
    for row in range(11):
        xs = range(11, 21) if row <= 4 else range(12, 20)
        for x in xs:
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            if row >= 9:
                shade = 0 if x >= 14 else 1
            b.put(x, yt + row, 'shirt', shade)
    for x in (15, 16, 17):
        b.put(x, yt, 'skin', 1)
    b.put(16, yt + 1, 'skin', 1)
    for x in (13, 14):
        b.put(x, yt + 3, 'shirt', 2)
    b.put(14, yt + 4, 'shirt', 2)
    for x in (17, 18):
        b.put(x, yt + 5, 'shirt', 0)
    # Skirt A-line paras lutut (role tetap 'skirt')
    last = 13 if seated else 19
    for row in range(11, last + 1):
        x0, x1 = (12, 19) if row <= 12 else (11, 20) if row <= 15 else (10, 21)
        for x in range(x0, x1 + 1):
            shade = 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1
            if row == 11:
                shade = 0
            if row >= 15 and x in (14, 17):
                shade = 0  # lipatan
            if row == 19:
                shade = 0
            b.put(x, yt + row, 'skirt', shade)


def torso_hiphop(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    last = 13 if seated else 15
    for row in range(last + 1):
        xs = range(10, 22) if row < 2 else range(9, 23)
        for x in xs:
            shade = 2 if x <= 10 else 0 if x >= 21 else 1
            if row >= 14:
                shade = 0
            b.put(x, yt + row, 'shirt', shade)
    # Leher bulat + rantai emas
    for x in range(13, 20):
        b.put(x, yt, 'shirt', 2)
    for x in (15, 16, 17):
        b.put(x, yt, 'skin', 1)
    b.put(16, yt + 1, 'skin', 1)
    b.put(14, yt + 1, 'shirt', 2)
    b.put(18, yt + 1, 'shirt', 2)
    b.put(15, yt + 2, 'gold', 1)
    b.put(16, yt + 3, 'gold', 2)
    b.put(17, yt + 2, 'gold', 1)
    # Cetakan di dada (hanya shading shirt)
    for x in (18, 19, 20):
        b.put(x, yt + 7, 'shirt', 2)
    for x in (18, 19):
        b.put(x, yt + 8, 'shirt', 2)


def torso_genz(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    last = 13 if seated else 15
    for row in range(last + 1):
        for x in range(10, 22):
            shade = 2 if x <= 11 else 0 if x >= 20 else 1
            if row >= 14:
                shade = 0
            b.put(x, yt + row, 'shirt', shade)
    # Cincin hood di leher
    for x, y in ((12, 0), (13, 0), (14, 0), (18, 0), (19, 0), (20, 0), (12, 1), (13, 1), (19, 1), (20, 1),
                 (13, 2), (19, 2), (14, 3), (18, 3), (13, 3), (19, 3)):
        b.put(x, yt + y, 'shirt', 2)
    for x, y in ((14, 1), (18, 1), (14, 2), (18, 2), (15, 3), (17, 3)):
        b.put(x, yt + y, 'shirt', 0)
    for y in (0, 1):
        for x in (15, 16, 17):
            b.put(x, yt + y, 'skin', 1)
    b.put(16, yt + 2, 'skin', 1)
    # tali hood + poket kangaroo
    for y in (4, 5, 6):
        b.put(15, yt + y, 'shirt', 2)
        b.put(17, yt + y, 'shirt', 2)
    if not seated:
        for x in range(12, 20):
            b.put(x, yt + 9, 'shirt', 0)
        b.put(12, yt + 10, 'shirt', 0)
        b.put(19, yt + 10, 'shirt', 0)


TORSO = {'default': torso_default, 'woman': torso_woman, 'hiphop': torso_hiphop, 'genz': torso_genz}


# ---- lengan -------------------------------------------------------------------

# x0 kiri / kanan (lengan tergantung), lebar, jumlah baris lengan baju, baris tangan,
# dan titik asas untuk gerakan menaip (tl/tr), serta bahu kanan (rs) untuk pose bengkok.
ARM = {
    'default': dict(lx=7, rx=22, w=3, sleeve=9, hand=2, hand_in=0, tl=8, tr=21, k_skin=99, rs=23, skin_from=0.65,
                    shl=(2, 1, 1), shr=(1, 1, 0)),
    'woman': dict(lx=7, rx=22, w=3, sleeve=5, hand=6, hand_in=0, tl=8, tr=21, k_skin=4, rs=23, skin_from=0.3,
                  shl=(2, 1, 1), shr=(1, 1, 0)),
    'hiphop': dict(lx=5, rx=23, w=4, sleeve=10, hand=2, hand_in=1, tl=6, tr=24, k_skin=99, rs=25, skin_from=0.85,
                   shl=(2, 1, 1, 0), shr=(2, 1, 1, 0)),
    'genz': dict(lx=5, rx=23, w=4, sleeve=10, hand=2, hand_in=1, tl=6, tr=24, k_skin=99, rs=25, skin_from=0.85,
                 shl=(2, 1, 1, 0), shr=(2, 1, 1, 0)),
}


def hang_arm(b, yt, x0, off, shades, A, cuff=False):
    w = len(shades)
    for row in range(A['sleeve']):
        for i in range(w):
            sh = 0 if (cuff and row == A['sleeve'] - 1) else shades[i]
            b.put(x0 + i, yt + 1 + off + row, 'shirt', sh)
    for row in range(A['hand']):
        for i in range(A['hand_in'], w - A['hand_in']):
            b.put(x0 + i, yt + 1 + A['sleeve'] + off + row, 'skin', 1)


def typing_arms(b, yt, typing, A):
    w = A['w']
    for side in (0, 1):
        raise_hand = (typing + side) % 2
        for k in range(8):
            shift = (k * 3) // 4
            xs = (A['tl'] + shift) if side == 0 else (A['tr'] - shift)
            for i in range(w):
                role = 'skin' if k >= A['k_skin'] else 'shirt'
                sh = 1 if role == 'skin' else 2 if (side == 0 and i == 0) else 0 if (side == 1 and i == w - 1) else 1
                b.put(xs + i - 1, yt + 1 + k, role, sh)
        hx = A['tl'] + 6 if side == 0 else A['tr'] - 6
        for i in range(2):
            for j in range(2):
                b.put(hx + i - 1, yt + 9 - raise_hand + j, 'skin', 1)


def bent_arm(b, S, E, H, A):
    """Lengan kanan bengkok S(bahu)->E(siku)->H(tangan); baju sampai skin_from, lepas itu kulit."""
    w = A['w']
    stroke(b, S, E, w, 'shirt', A['shr'])
    f = A['skin_from']
    Hs = (E[0] + int(round((H[0] - E[0]) * f)), E[1] + int(round((H[1] - E[1]) * f)))
    stroke(b, E, Hs, w, 'shirt', (2,) + A['shr'][1:])
    stroke(b, Hs, H, 2, 'skin', (1,))
    b.put(H[0], H[1], 'skin', 1)


def pose_arm(b, yt, pose, A):
    sx, sy = A['rs'], yt + 2
    for row in range(1, 4):  # pangkal bahu (supaya lengan sentiasa bersambung dengan badan)
        for i in range(A['w']):
            b.put(A['rx'] + i, yt + row, 'shirt', A['shr'][i])
    if pose == 'dart0':    # tangan ditarik ke belakang/atas, dekat telinga
        bent_arm(b, (sx, sy), (sx + 3, sy + 3), (sx + 3, yt - 3), A)
    elif pose == 'dart1':  # tangan dilontar ke hadapan (lurus ke luar/atas)
        hx = min(sx + 6, 29)
        bent_arm(b, (sx, sy - 1), ((sx + hx) // 2 + 1, sy - 2), (hx, sy - 5), A)
    elif pose == 'drink0':  # cawan putih di mulut
        bent_arm(b, (sx, sy), (sx + 1, yt + 5), (20, yt - 1), A)
        cup(b, yt, 0)
    else:                   # drink1: cawan senget sikit
        bent_arm(b, (sx, sy), (sx + 1, yt + 5), (20, yt - 2), A)
        cup(b, yt, 1)


def cup(b, yt, tilt):
    """Cawan putih kecil (role tetap 'cup') di mulut; tilt = senget sikit."""
    ox, oy = (-1, -1) if tilt else (0, 0)
    for r in range(5):
        x0, x1 = (17, 20) if r < 4 else (18, 19)
        for x in range(x0, x1 + 1):
            sh = 2 if (r == 0 or x == x0) else 0 if x == x1 else 1
            if r == 0 and x != x0 and x != x1:
                sh = 0  # permukaan kopi/air
            b.put(x + ox + (r // 2 if tilt else 0) * 0, yt - 6 + r + oy, 'cup', sh)


# ---- kaki ---------------------------------------------------------------------

def legs_default(b, lx, rx, llift, rlift):
    for x0, off, lift, shades in ((11, lx, llift, (2, 1, 1, 1, 0)), (16, rx, rlift, (1, 1, 1, 1, 0))):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            for i in range(5):
                b.put(x0 + off + i, y, 'pants', shades[i])
        for y in range(bottom + 1, bottom + 4):
            for i in range(-1 if x0 == 11 else 0, 6 if x0 == 16 else 5):
                b.put(x0 + off + i, y, 'shoes', 0 if y == bottom + 3 else 1)


def legs_woman(b, lx, rx, llift, rlift):
    # Kaki kulit kosong + kasut flat kecil
    for x0, off, lift, shades in ((12, lx, llift, (2, 1, 0)), (17, rx, rlift, (2, 1, 0))):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            for i in range(3):
                b.put(x0 + off + i, y, 'skin', shades[i] if y < bottom - 1 else 1)
        for y in range(bottom + 1, bottom + 4):
            lo = x0 - 1 if x0 == 12 else x0
            hi = x0 + 2 if x0 == 12 else x0 + 3
            if y == bottom + 1:
                lo, hi = x0, x0 + 2
            for x in range(lo, hi + 1):
                b.put(x + off, y, 'shoes', 0 if y == bottom + 3 else 1)


def sneakers(b, x0, off, bottom, left):
    lo, hi = (x0 - 1, x0 + 5) if left else (x0, x0 + 6)
    for x in range(lo + 1, hi):
        b.put(x + off, bottom + 1, 'sneakers', 2)
    for x in range(lo, hi + 1):
        b.put(x + off, bottom + 2, 'sneakers', 1)
        b.put(x + off, bottom + 3, 'sneakers', 0)
    b.put((lo if left else hi) + off, bottom + 2, 'sneakers', 2)
    b.put(x0 + 2 + off, bottom + 1, 'sneakers', 1)


def legs_hiphop(b, lx, rx, llift, rlift):
    for x0, off, lift, left in ((10, lx, llift, True), (16, rx, rlift, False)):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            gather = y >= bottom - 1
            for i in range(-1 if (gather and left) else 0, 7 if (gather and not left) else 6):
                sh = 2 if i <= 0 else 0 if i >= 5 else 1
                if y == bottom - 3:
                    sh = 0  # lipatan seluar
                b.put(x0 + off + i, y, 'pants2', sh)
        sneakers(b, x0, off, bottom, left)


def legs_genz(b, lx, rx, llift, rlift):
    for x0, off, lift, left in ((10, lx, llift, True), (16, rx, rlift, False)):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            flare = y >= bottom - 4
            for i in range(-1 if (flare and left) else 0, 7 if (flare and not left) else 6):
                sh = 2 if i <= 0 else 0 if i >= 5 else 1
                if i == 2 and not flare:
                    sh = 2  # jahitan denim
                if y == bottom:
                    sh = 0
                b.put(x0 + off + i, y, 'pants', sh)
        sneakers(b, x0, off, bottom, left)


LEGS = {'default': legs_default, 'woman': legs_woman, 'hiphop': legs_hiphop, 'genz': legs_genz}


def extras_front(b, style, y0):
    if style == 'woman':  # hujung rambut jatuh di atas bahu (lukis paling akhir)
        for row in range(11, 15):
            for x, sh in ((10, 0), (11, 1), (12, 2), (20, 2), (21, 1), (22, 0)):
                if row == 14 and x in (11, 21):
                    continue
                b.put(x, y0 + row, 'hair', sh)
        for x in (11, 21):
            b.put(x, y0 + 15, 'hair', 0)


def figure(dy=0, seated=False, lx=0, rx=0, llift=0, rlift=0, al=0, ar=0, typing=None, pose=None, style='default'):
    """Satu frame (depan). pose: None | dart0 | dart1 | drink0 | drink1. style: default/woman/hiphop/genz."""
    b = Buf()
    y0 = 6 + dy
    yt = y0 + 12
    A = ARM[style]

    if style != 'default' and not seated:
        LEGS[style](b, lx, rx, llift, rlift)  # seluar/kaki dulu supaya baju/skirt menutup

    HEAD[style](b, y0)
    TORSO[style](b, yt, seated)

    if pose:
        hang_arm(b, yt, A['lx'], 0, A['shl'], A, cuff=style in ('hiphop', 'genz'))
        pose_arm(b, yt, pose, A)
    elif typing is None:
        cuff = style in ('hiphop', 'genz')
        hang_arm(b, yt, A['lx'], al, A['shl'], A, cuff)
        hang_arm(b, yt, A['rx'], ar, A['shr'], A, cuff)
    else:
        typing_arms(b, yt, typing, A)

    if style == 'default' and not seated:
        LEGS[style](b, lx, rx, llift, rlift)

    extras_front(b, style, y0)
    if pose in ('drink0', 'drink1'):
        pose_cup_redraw(b, yt, pose)

    return add_outline(b)


def pose_cup_redraw(b, yt, pose):
    cup(b, yt, 0 if pose == 'drink0' else 1)


# ---- pandangan belakang (duduk menghadap meja) ---------------------------------------

def back_head_default(b, y0):
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


def back_head_woman(b, y0):
    # Rambut menutup seluruh belakang kepala dan jatuh ke belikat
    for row in range(11):
        x0, x1 = (12, 20) if row == 0 else (11, 21) if row <= 8 else (11, 21)
        for x in range(x0, x1 + 1):
            b.put(x, y0 + row, 'hair', 2 if row <= 2 else 1 if row <= 6 else 0 if x in (x0, x1) else 1)
    for row in (4, 5):
        b.put(10, y0 + row, 'skin', 1)
        b.put(22, y0 + row, 'skin', 0)


def back_hair_fall(b, y0):
    """Rambut panjang woman jatuh ke belikat (lukis selepas badan supaya menutup baju)."""
    for row in range(9, 21):
        x0, x1 = (11, 21) if row <= 10 else (12, 20) if row <= 16 else (13, 19) if row <= 18 else (14, 18)
        for x in range(x0, x1 + 1):
            sh = 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1
            if row >= 19:
                sh = 0
            b.put(x, y0 + row, 'hair', sh)


def back_head_hiphop(b, y0):
    for row in range(11):
        x0, x1 = (12, 20) if row in (0, 9) else (13, 19) if row == 10 else (11, 21)
        for x in range(x0, x1 + 1):
            if row <= 4:
                b.put(x, y0 + row, 'cap', 2 if (row == 1 and x in (13, 14)) else 0 if x in (11, 21) else 1)
            elif row == 5:
                # jurang strap snapback: celah nampak rambut di tengah
                if 14 <= x <= 18:
                    b.put(x, y0 + row, 'hair', 0)
                else:
                    b.put(x, y0 + row, 'cap', 0)
            else:
                b.put(x, y0 + row, 'hair', 1 if row <= 7 else 0)
    for x in (14, 18):
        b.put(x, y0 + 5, 'cap', 2)  # hujung strap plastik
    b.put(16, y0, 'cap', 2)
    for x in (13, 14, 15, 16, 17, 18, 19):
        b.put(x, y0 + 8, 'hair', 0)
    for x in (14, 15, 16, 17, 18):
        b.put(x, y0 + 10, 'skin', 0)
    for row in (6, 7):
        b.put(10, y0 + row, 'skin', 1)
        b.put(22, y0 + row, 'skin', 0)


def back_head_genz(b, y0):
    for x in range(12, 21):
        b.put(x, y0 - 2, 'hair', 2 if x <= 15 else 1)
    for row in range(-1, 3):
        for x in range(10, 23):
            sh = 2 if (row in (-1, 0) and 12 <= x <= 15) else 0 if x in (10, 22) else 1
            b.put(x, y0 + row, 'hair', sh)
    for row in range(3, 7):
        for x in range(11, 22):
            b.put(x, y0 + row, 'hair', 1)
    for row in range(7, 10):  # undercut tengkuk
        x0, x1 = (12, 20) if row == 9 else (11, 21)
        for x in range(x0, x1 + 1):
            b.put(x, y0 + row, 'hair', 0 if (row == 9 or 12 <= x <= 20) else 1)
    for x in (14, 15, 16, 17, 18):
        b.put(x, y0 + 10, 'skin', 0)
    phones(b, y0)


BACK_HEAD = {'default': back_head_default, 'woman': back_head_woman, 'hiphop': back_head_hiphop, 'genz': back_head_genz}

BACK_ARM = {
    'default': dict(lx=8, rx=21, w=3, skin_from=99, shl=(2, 1, 1), shr=(1, 1, 0)),
    'woman': dict(lx=8, rx=21, w=3, skin_from=5, shl=(2, 1, 1), shr=(1, 1, 0)),
    'hiphop': dict(lx=5, rx=23, w=4, skin_from=99, shl=(2, 1, 1, 0), shr=(2, 1, 1, 0)),
    'genz': dict(lx=5, rx=23, w=4, skin_from=99, shl=(2, 1, 1, 0), shr=(2, 1, 1, 0)),
}


def figure_back(typing=0, style='default'):
    """Duduk dari belakang, menghadap meja (macam staff dalam gambar rujukan)."""
    b = Buf()
    y0 = 10
    BACK_HEAD[style](b, y0)

    yt = y0 + 12
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    if style == 'default':
        for row in range(14):
            for x in range(11, 21):
                shade = 2 if x <= 12 else 0 if x >= 19 else 1
                b.put(x, yt + row, 'shirt', shade)
        for x in range(13, 20):
            b.put(x, yt, 'shirt', 0)
            b.put(x, yt + 1, 'shirt', 0)
        for x in range(14, 19):
            b.put(x, yt + 2, 'shirt', 0)
    elif style == 'woman':
        for row in range(11):
            xs = range(11, 21) if row <= 4 else range(12, 20)
            for x in xs:
                shade = 2 if x <= 12 else 0 if x >= 19 else 1
                if row >= 9:
                    shade = 0
                b.put(x, yt + row, 'shirt', shade)
        for row in range(11, 14):
            x0, x1 = (12, 19) if row <= 12 else (11, 20)
            for x in range(x0, x1 + 1):
                b.put(x, yt + row, 'skirt', 0 if row == 11 else 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1)
    elif style == 'hiphop':
        for row in range(14):
            xs = range(10, 22) if row < 2 else range(9, 23)
            for x in xs:
                shade = 2 if x <= 10 else 0 if x >= 21 else 1
                if row >= 12:
                    shade = 0
                b.put(x, yt + row, 'shirt', shade)
        for x in range(13, 20):
            b.put(x, yt, 'shirt', 2)
    else:  # genz: hood nampak dari belakang
        for row in range(14):
            for x in range(10, 22):
                shade = 2 if x <= 11 else 0 if x >= 20 else 1
                if row >= 12:
                    shade = 0
                b.put(x, yt + row, 'shirt', shade)
        for row, (x0, x1) in enumerate(((12, 19), (12, 19), (13, 18), (14, 17), (15, 16))):
            for x in range(x0, x1 + 1):
                b.put(x, yt + row, 'shirt', 0)
        for x in range(12, 20):
            b.put(x, yt, 'shirt', 2 if x in (12, 13, 18, 19) else 0)

    A = BACK_ARM[style]
    w = A['w']
    for side, x0 in ((0, A['lx']), (1, A['rx'])):
        lift = (typing + side) % 2
        shades = A['shl'] if side == 0 else A['shr']
        for row in range(7):
            skin = row >= A['skin_from']
            for i in range(w):
                b.put(x0 + i, yt + 1 + row - lift, 'skin' if skin else 'shirt', 1 if skin else shades[i])
    if style == 'woman':
        back_hair_fall(b, y0)

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
    # 10-11: berdiri sambil bermain (tangan ke depan, bergilir). Guna lengan "typing" tetapi dengan kaki.
    dict(typing=0),
    dict(typing=1),
    # 12-13: lontar dart (12 = tarik ke belakang, 13 = lontar ke hadapan), kaki tetap.
    dict(pose='dart0'),
    dict(pose='dart1'),
    # 14-15: minum (cawan putih di mulut; 15 senget sikit)
    dict(pose='drink0'),
    dict(pose='drink1'),
]


def staff_sheets(style='default'):
    """Pulangkan {fixed, skin, hair, shirt: Image 512x48} untuk satu style."""
    sheets = {name: Image.new('RGBA', (FW * len(FRAMES), FH), (0, 0, 0, 0)) for name in ('fixed', 'skin', 'hair', 'shirt')}
    for index, pose in enumerate(FRAMES):
        buf = figure_back(pose['typing'], style) if pose.get('back') else figure(style=style, **pose)
        for (x, y), (role, shade) in buf.px.items():
            ox = index * FW + x
            if role in FIXED:
                sheets['fixed'].putpixel((ox, y), FIXED[role][shade] if shade in FIXED[role] else FIXED[role][1])
            else:
                level = int(255 * TINT_LEVELS[role][shade])
                sheets[role].putpixel((ox, y), (level, level, level, 255))
    return sheets


def all_staff_sheets():
    """{ 'staff_fixed': img, 'staff_woman_skin': img, ... } untuk semua 4 style."""
    out = {}
    for style in STYLES:
        for layer, img in staff_sheets(style).items():
            out[f'{SHEET_PREFIX[style]}_{layer}'] = img
    return out



# ---------------------------------------------------------------- furniture

# Palet gaya pejabat Google: putih bersih, kayu maple cerah, aksen biru/merah/kuning/hijau.
G_BLUE, G_RED, G_YELLOW, G_GREEN = (66, 133, 244, 255), (234, 67, 53, 255), (251, 188, 5, 255), (52, 168, 83, 255)
GOOGLE = {'blue': G_BLUE, 'red': G_RED, 'yellow': G_YELLOW, 'green': G_GREEN}


def shade(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color[:3]) + (255,)


# Meja: permukaan putih, sisi maple
WOOD = dict(top=(248, 246, 240, 255), hi=(255, 255, 255, 255), left=(224, 198, 152, 255), right=(192, 162, 114, 255))
MAPLE = dict(top=(236, 218, 184, 255), hi=(250, 238, 212, 255), left=(214, 188, 142, 255), right=(184, 154, 108, 255))
WHITE = dict(top=(250, 250, 250, 255), hi=(255, 255, 255, 255), left=(226, 228, 232, 255), right=(196, 200, 206, 255))


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
        d.line([(cx + dx, cy - 14 + 8), (cx + dx + 10, cy - 14 + 3)], fill=(232, 228, 218, 255))
    # Laci pada muka kanan
    d.line([(cx + 4, cy - 6 + 5), (cx + 24, cy - 6 - 5)], fill=OL)
    d.rectangle([cx + 12, cy - 3, cx + 15, cy - 1], fill=G_BLUE)
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


def chair(color=G_BLUE):
    """Kerusi pejabat dilihat dari belakang. Tanah pada y=37. Sandaran rendah supaya
    kepala dan bahu staff yang duduk nampak di atasnya. Warna ikut palet Google."""
    img, d = new(32, 40)
    base = (96, 100, 108, 255)
    for end in ((5, 37), (27, 37), (10, 39), (22, 39)):
        d.line([(16, 34), end], fill=base, width=2)
    for x in (5, 27, 10, 22):
        d.point((x, 38 if x in (5, 27) else 39), fill=(40, 40, 46, 255))
    d.rectangle([15, 27, 17, 34], fill=(120, 124, 132, 255))
    d.rounded_rectangle([5, 23, 27, 28], radius=2, fill=shade(color, 0.82), outline=OL)
    d.rectangle([3, 20, 6, 27], fill=shade(color, 0.7), outline=OL)
    d.rectangle([26, 20, 29, 27], fill=shade(color, 0.7), outline=OL)
    d.rounded_rectangle([8, 12, 24, 25], radius=3, fill=color, outline=OL)
    d.line([(10, 14), (22, 14)], fill=shade(color, 1.25))
    d.line([(10, 15), (10, 22)], fill=shade(color, 1.12))
    return img


def partition():
    """Dinding separuh (partition) sepanjang paksi c, macam bilik dalam gambar rujukan.
    Tile center pada (28, 66). Flip mendatar untuk paksi r."""
    img, d = new(56, 80)
    cream, cap, base, edge = (250, 250, 252, 255), (255, 255, 255, 255), G_BLUE, (214, 218, 224, 255)
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
    d.polygon([(14, 46), (34, 46), (31, 60), (17, 60)], fill=(244, 244, 246, 255), outline=OL)
    d.rectangle([12, 43, 35, 47], fill=(255, 255, 255, 255), outline=OL)
    d.line([(16, 52), (30, 52)], fill=G_YELLOW)
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
    cx, cy = box(d, 70, 42, (244, 240, 230, 255), (232, 214, 180, 255), (206, 184, 144, 255), (255, 255, 255, 255))
    books = [(234, 67, 53), (66, 133, 244), (52, 168, 83), (251, 188, 5), (66, 133, 244), (234, 67, 53), (52, 168, 83)]
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


def sofa(color=G_RED):
    img, d = new(56, 58)
    cx, cy = 28, 58 - 14
    t, l, r = shade(color, 1.08), shade(color, 0.78), shade(color, 0.6)
    d.polygon([(cx - 28, cy - 12), (cx, cy - 12 - 14), (cx, cy - 12 - 14 - 16), (cx - 28, cy - 12 - 16)], fill=l, outline=OL)
    d.polygon([(cx, cy - 12 - 14), (cx + 28, cy - 12), (cx + 28, cy - 12 - 16), (cx, cy - 12 - 14 - 16)], fill=r, outline=OL)
    box(d, 58, 12, t, l, r, shade(color, 1.3))
    d.line([(cx, cy - 12 - 14), (cx, cy - 12 + 14)], fill=l)
    return img


def machine():
    img, d = new(56, 68)
    cx, cy = box(d, 68, 18, WHITE['top'], MAPLE['left'], MAPLE['right'], WHITE['hi'])
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
    cx, cy = box(d, 42, 6, G_BLUE, shade(G_BLUE, 0.7), shade(G_BLUE, 0.55))
    d.polygon([(cx, cy - 6 - 11), (cx + 22, cy - 6), (cx, cy - 6 + 11), (cx - 22, cy - 6)], outline=(240, 240, 240, 255))
    d.line([(cx - 11, cy - 6 - 6), (cx + 11, cy - 6 + 6)], fill=(240, 240, 240, 255))
    d.line([(cx - 12, cy - 6 - 6), (cx - 12, cy - 6 - 11)], fill=(200, 200, 210, 255))
    d.line([(cx + 10, cy - 6 + 6), (cx + 10, cy - 6 + 1)], fill=(200, 200, 210, 255))
    return img


def foos():
    img, d = new(56, 46)
    cx, cy = box(d, 46, 10, G_GREEN, shade(G_GREEN, 0.72), shade(G_GREEN, 0.56), (140, 214, 160, 255))
    for k in range(-2, 3):
        d.line([(cx + k * 4 - 8, cy - 10 + k * 2 + 6), (cx + k * 4 + 8, cy - 10 + k * 2 - 2)], fill=(200, 200, 210, 255))
    for k in range(-2, 3):
        d.rectangle([cx + k * 4, cy - 10 + k * 2 + 2, cx + k * 4 + 1, cy - 10 + k * 2 + 3], fill=(220, 60, 50, 255))
    return img


def table():
    img, d = new(56, 52)
    cx, cy = box(d, 52, 10, WOOD['top'], MAPLE['left'], MAPLE['right'], WOOD['hi'])
    d.polygon([(cx - 10, cy - 10), (cx, cy - 15), (cx + 8, cy - 11), (cx - 2, cy - 6)], fill=(236, 232, 218, 255), outline=OL)
    d.rectangle([cx + 6, cy - 22, cx + 14, cy - 15], fill=(60, 60, 70, 255), outline=OL)
    d.polygon([(cx + 4, cy - 10), (cx + 13, cy - 8), (cx + 8, cy - 4), (cx - 1, cy - 6)], fill=(110, 190, 150, 255), outline=OL)
    return img


def reception():
    img, d = new(56, 58)
    cx, cy = box(d, 58, 16, WHITE['top'], G_BLUE, shade(G_BLUE, 0.72), WHITE['hi'])
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


def left_pt(cy, h, x, dy):
    """Titik pada muka kiri box: x (0..28) dan dy dari bucu atas muka (garis condong 1px / 2px)."""
    return (x, cy - h + x // 2 + dy)


def glyph_left(img, x0, y0, rows, color):
    """Huruf bitmap kecil pada muka kiri (condong ikut kecerunan 1:2)."""
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch == 'X':
                x = x0 + gx
                img.putpixel((x, y0 + gy + x // 2), color)


def snooker():
    """Meja snooker SATU tile: rel kayu gelap, felt hijau, bola. Disusun sebelah-menyebelah oleh frontend."""
    img, d = new(56, 42)
    wood = dict(top=(96, 58, 34, 255), left=(74, 42, 24, 255), right=(56, 30, 18, 255))
    cx, cy = box(d, 42, 14, wood['top'], wood['left'], wood['right'], (140, 92, 58, 255))
    ty = cy - 14  # pusat muka atas
    felt, felt_d = (30, 130, 70, 255), (24, 108, 58, 255)
    d.polygon([(cx, ty - 10), (cx + 24, ty), (cx, ty + 10), (cx - 24, ty)], fill=felt, outline=felt_d)
    d.line([(cx - 20, ty - 1), (cx, ty - 9)], fill=(48, 156, 90, 255))
    d.line([(cx - 27, ty + 6), (cx - 1, ty + 19)], fill=(104, 62, 36, 255))
    d.line([(cx + 1, ty + 19), (cx + 27, ty + 6)], fill=(78, 44, 26, 255))
    balls = [((cx - 6, ty - 2), (220, 40, 40)), ((cx - 3, ty - 1), (220, 40, 40)), ((cx + 2, ty + 1), (30, 30, 30)),
             ((cx + 8, ty - 3), (250, 210, 40)), ((cx - 10, ty + 3), (60, 120, 220)), ((cx + 11, ty + 2), (230, 130, 190))]
    for (x, y), col in balls:
        d.point((x, y), fill=col + (255,))
        d.point((x + 1, y), fill=col + (255,))
    d.point((cx + 12, ty - 1), fill=(255, 255, 255, 255))  # bola putih (cue)
    d.point((cx + 13, ty - 1), fill=(255, 255, 255, 255))
    return img


def fridge():
    img, d = new(56, 74)
    cx, cy = box(d, 74, 46, (240, 242, 246, 255), (232, 235, 240, 255), (198, 203, 212, 255), (255, 255, 255, 255))
    # pintu: garisan pemisah freezer / pintu bawah
    d.line([left_pt(cy, 46, 1, 15), left_pt(cy, 46, 27, 15)], fill=(150, 156, 168, 255))
    d.line([left_pt(cy, 46, 1, 16), left_pt(cy, 46, 27, 16)], fill=(255, 255, 255, 255))
    # pemegang (2 batang kelabu) dan magnet kecil warna Google
    for hy in (8, 20):
        for x in (23, 24):
            y = cy - 46 + x // 2 + hy
            d.line([(x, y), (x, y + 6)], fill=(110, 116, 128, 255))
    for (x, dy, col) in ((6, 24, G_RED), (11, 28, G_BLUE), (8, 32, G_YELLOW)):
        y = cy - 46 + x // 2 + dy
        d.rectangle([x, y, x + 1, y + 1], fill=col)
    for x in range(12, 17):  # kertas nota
        d.point((x, cy - 46 + x // 2 + 5), fill=(250, 246, 232, 255))
        d.point((x, cy - 46 + x // 2 + 6), fill=(250, 246, 232, 255))
    d.line([(31, cy - 46 + 14 + 3 + 1), (53, cy - 46 + 3)], fill=(176, 182, 194, 255))
    return img


def wc():
    """Bilik tandas: partition putih 44px, pintu panel biru dengan plat 'WC', sedikit mangkuk nampak di atas."""
    img, d = new(56, 72)
    cx, cy = box(d, 72, 44, (250, 250, 252, 255), (240, 242, 246, 255), (204, 208, 216, 255), (255, 255, 255, 255))
    h = 44
    d.polygon([left_pt(cy, h, 4, 7), left_pt(cy, h, 24, 7), left_pt(cy, h, 24, h - 4), left_pt(cy, h, 4, h - 4)],
              fill=G_BLUE, outline=OL)
    d.line([left_pt(cy, h, 6, 9), left_pt(cy, h, 22, 9)], fill=(120, 168, 250, 255))
    d.polygon([left_pt(cy, h, 6, 12), left_pt(cy, h, 22, 12), left_pt(cy, h, 22, 22), left_pt(cy, h, 6, 22)],
              fill=(250, 250, 252, 255), outline=OL)
    base = cy - h + 14
    glyph_left(img, 8, base, ["X...X", "X...X", "X.X.X", "XX.XX", "X...X"], (24, 54, 120, 255))
    glyph_left(img, 15, base, ["XXX", "X..", "X..", "X..", "XXX"], (24, 54, 120, 255))
    for dy in (26, 27):  # pemegang pintu
        img.putpixel((22, cy - h + 11 + dy), (250, 204, 21, 255))
    d.rectangle([40, cy - h + 20, 43, cy - h + 22], fill=G_GREEN)
    d.polygon([(cx - 5, cy - h - 11), (cx + 5, cy - h - 11), (cx + 5, cy - h - 7), (cx - 5, cy - h - 7)],
              fill=(255, 255, 255, 255), outline=OL)
    d.rectangle([cx - 3, cy - h - 10, cx + 3, cy - h - 9], fill=(210, 232, 250, 255))
    return img


def sink():
    img, d = new(56, 46)
    cx, cy = box(d, 46, 18, (250, 250, 250, 255), (228, 214, 186, 255), (194, 176, 144, 255), (255, 255, 255, 255))
    ty = cy - 18
    d.polygon([(cx, ty - 7), (cx + 14, ty), (cx, ty + 7), (cx - 14, ty)], fill=(176, 206, 226, 255), outline=(110, 130, 150, 255))
    d.polygon([(cx, ty - 4), (cx + 8, ty), (cx, ty + 4), (cx - 8, ty)], fill=(130, 170, 200, 255))
    # pili air (batang logam + muncung) di belakang besen
    d.line([(cx, ty - 9), (cx, ty - 14)], fill=(176, 180, 190, 255), width=2)
    d.line([(cx, ty - 14), (cx + 4, ty - 12)], fill=(176, 180, 190, 255), width=2)
    d.point((cx - 3, ty - 12), fill=G_BLUE)
    d.point((cx + 3, ty - 13), fill=G_RED)
    d.line([left_pt(cy, 18, 4, 3), left_pt(cy, 18, 24, 3)], fill=(176, 154, 116, 255))
    d.line([left_pt(cy, 18, 4, 14), left_pt(cy, 18, 24, 14)], fill=(176, 154, 116, 255))
    return img


def boardtable():
    """Satu keping meja mesyuarat panjang: walnut gelap berkilat."""
    img, d = new(56, 40)
    cx, cy = box(d, 40, 12, (96, 58, 38, 255), (66, 38, 24, 255), (48, 27, 17, 255), (150, 104, 74, 255))
    ty = cy - 12
    d.line([(cx - 18, ty - 2), (cx - 4, ty - 9)], fill=(130, 86, 58, 255))  # sinar licin
    d.line([(cx - 14, ty), (cx + 2, ty - 8)], fill=(112, 70, 46, 255))
    d.point((cx - 10, ty - 6), fill=(190, 146, 112, 255))
    d.polygon([(cx - 14, ty + 1), (cx - 7, ty - 2), (cx - 2, ty), (cx - 9, ty + 3)], fill=(246, 244, 236, 255), outline=OL)
    d.line([(cx - 11, ty + 1), (cx - 6, ty - 1)], fill=(160, 170, 184, 255))
    d.polygon([(cx + 4, ty + 1), (cx + 13, ty - 3), (cx + 18, ty - 1), (cx + 9, ty + 3)], fill=(178, 182, 190, 255), outline=OL)
    d.polygon([(cx + 5, ty - 1), (cx + 13, ty - 5), (cx + 13, ty - 9), (cx + 5, ty - 5)], fill=(40, 44, 56, 255), outline=OL)
    d.line([(cx + 6, ty - 4), (cx + 12, ty - 7)], fill=(100, 160, 240, 255))
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
    d.polygon(pts, outline=(190, 170, 136, 255))
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
    frame = (240, 242, 246, 255)
    d.rectangle([0, 0, 44, 57], fill=frame, outline=OL)
    for y in range(3, 52):
        t = (y - 3) / 48
        col = (int(176 + 60 * t), int(212 + 36 * t), 255, 255)  # langit siang: biru muda ke putih
        d.line([(3, y), (41, y)], fill=col)
    for y in range(5, 30, 4):
        d.line([(3, y), (41, y)], fill=(206, 224, 244, 255))  # bidai
    d.rectangle([21, 3, 23, 51], fill=frame)
    d.rectangle([3, 30, 41, 32], fill=frame)
    d.rectangle([0, 52, 44, 57], fill=(214, 218, 224, 255), outline=OL)
    d.line([(4, 5), (14, 5)], fill=(255, 255, 255, 255))
    return img


def wall_board():
    img, d = new(73, 58)
    d.rectangle([0, 0, 72, 57], fill=(226, 228, 232, 255), outline=OL)
    d.rectangle([3, 3, 69, 49], fill=(250, 251, 252, 255), outline=(176, 180, 188, 255))
    d.rectangle([3, 51, 69, 55], fill=G_BLUE)
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


def wall_dartboard():
    """Papan dart bulat ~36px pada pelapik gabus; kemudian di-shear untuk dinding B."""
    img, d = new(44, 44)
    d.rectangle([0, 0, 43, 43], fill=(226, 214, 192, 255), outline=OL)
    d.rectangle([2, 2, 41, 41], fill=(206, 166, 108, 255))
    rnd = random.Random(5)
    for _ in range(30):
        d.point((rnd.randint(3, 40), rnd.randint(3, 40)), fill=(184, 144, 90, 255))
    cx = cy = 22
    cream, black = (244, 232, 196, 255), (34, 32, 34, 255)
    red, green = G_RED, G_GREEN

    def ring(r_out, c_even, c_odd):
        for k in range(20):
            col = c_even if k % 2 == 0 else c_odd
            d.pieslice([cx - r_out, cy - r_out, cx + r_out, cy + r_out], -99 + k * 18, -99 + (k + 1) * 18, fill=col)

    d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=black, outline=OL)  # bezel
    ring(16, red, green)       # double
    ring(13, black, cream)     # single luar
    ring(9, red, green)        # treble
    ring(6, black, cream)      # single dalam
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=green)  # bull luar
    d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=red)    # bullseye
    # 3 anak panah tercucuk (batang + sirip berwarna)
    for (x, y, col) in ((cx + 1, cy - 1, G_YELLOW), (cx - 7, cy - 4, G_BLUE), (cx + 6, cy + 7, (250, 250, 250, 255))):
        d.line([(x, y), (x - 4, y - 5)], fill=(150, 156, 168, 255))
        d.rectangle([x - 7, y - 8, x - 5, y - 6], fill=col, outline=OL)
        d.point((x, y), fill=(60, 60, 66, 255))
    return img


def build(preview=None):
    OUT.mkdir(parents=True, exist_ok=True)

    walls = {
        'wall_window_a': shear(wall_window(), 'A'), 'wall_window_b': shear(wall_window(), 'B'),
        'wall_board_a': shear(wall_board(), 'A'), 'wall_cork_b': shear(wall_cork(), 'B'),
        'wall_poster_a1': shear(wall_poster('chart'), 'A'), 'wall_poster_a2': shear(wall_poster('sun'), 'A'),
        'wall_poster_b': shear(wall_poster('sun'), 'B'), 'wall_logo_b': shear(wall_logo(), 'B'),
        'wall_dartboard_b': shear(wall_dartboard(), 'B'),
        'brand_logo': wall_logo(),
        'partition_a': partition(), 'partition_b': partition().transpose(Image.FLIP_LEFT_RIGHT),
        'partition_a_logo': partition_poster(), 'partition_b_logo': partition_poster().transpose(Image.FLIP_LEFT_RIGHT),
    }
    for name, img in walls.items():
        img.save(OUT / f'{name}.png')

    staff = all_staff_sheets()
    for name, sheet in staff.items():
        sheet.save(OUT / f'{name}.png')

    assets = {
        'desk': desk(), 'plant': plant(), 'shelf': shelf(), 'cooler': cooler(),
        'machine': machine(), 'server': server(), 'pong': pong(), 'foos': foos(),
        **{f'chair_{name}': chair(color) for name, color in GOOGLE.items()},
        **{f'sofa_{name}': sofa(color) for name, color in GOOGLE.items()},
        'table': table(), 'reception': reception(), 'bell': bell(),
        'snooker': snooker(), 'fridge': fridge(), 'wc': wc(), 'sink': sink(), 'boardtable': boardtable(),
        'floor_a': floor_tile((238, 224, 196, 255), 1), 'floor_b': floor_tile((226, 208, 174, 255), 2),
    }
    for name, img in assets.items():
        img.save(OUT / f'{name}.png')

    print(f'{len(assets) + len(walls) + len(staff)} fail ditulis ke {OUT}')

    if preview:
        make_preview(Path(preview), {**assets, 'wall_dartboard_b': walls['wall_dartboard_b']})


def make_preview(folder, assets):
    folder.mkdir(parents=True, exist_ok=True)

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
              ((139, 92, 246), (217, 165, 119), (31, 41, 55)), ((234, 67, 53), (245, 208, 176), (161, 98, 7))]

    def style_strip(style, rows=combos):
        prefix = SHEET_PREFIX[style]
        sheets = {n: Image.open(OUT / f'{prefix}_{n}.png') for n in ('fixed', 'skin', 'hair', 'shirt')}
        strip = Image.new('RGBA', (FW * len(FRAMES), FH * len(rows)), (200, 160, 110, 255))
        for row, (shirt, skin, hair) in enumerate(rows):
            for layer, color in (('skin', skin), ('hair', hair), ('shirt', shirt)):
                strip.alpha_composite(tint(sheets[layer], color), (0, row * FH))
            strip.alpha_composite(sheets['fixed'], (0, row * FH))
        return strip

    strips = {style: style_strip(style) for style in STYLES}
    for style, strip in strips.items():
        strip.resize((strip.width * 4, strip.height * 4), Image.NEAREST).save(folder / f'preview_staff_{style}.png')
    strips['default'].resize((strips['default'].width * 4, strips['default'].height * 4), Image.NEAREST).save(folder / 'preview_staff.png')
    # Semua style x 2 tint, saiz 2x (untuk semak sekilas)
    two = Image.new('RGBA', (FW * len(FRAMES), FH * 2 * len(STYLES)), (200, 160, 110, 255))
    for i, style in enumerate(STYLES):
        two.alpha_composite(strips[style].crop((0, 0, strips[style].width, FH * 2)), (0, i * FH * 2))
    two.resize((two.width * 2, two.height * 2), Image.NEAREST).save(folder / 'preview_staff_all.png')

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
