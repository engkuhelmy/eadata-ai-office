#!/usr/bin/env python3
"""Jana aset sprite pixel art untuk AI Office Hub (original, gaya rujukan: kayu hangat, outline gelap).

Guna: python tools/make_sprites.py [--preview DIR]
Output: public/assets/office/*.png

Staff dipecah kepada 4 lapisan supaya boleh diwarnakan (tint) dalam Phaser:
  staff_fixed (outline, seluar, kasut, mata), staff_skin, staff_hair, staff_shirt (warna vendor).
Setiap sheet: 16 frame 32x48 dalam satu baris: 0-1 idle, 2-5 walk, 6-7 duduk depan, 8-9 duduk belakang,
10-11 main/hulur, 12-13 dart, 14-15 minum.
Gaya vendor/pelawat (recep, grab, shopee, jnt, dhl) -> staff_{style}_{fixed|skin|hair|shirt}.png.
Prop tambahan: wall_door_b.png (pintu masuk dinding B), counter_parcels.png (barang hantaran atas kaunter).
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
STYLES = ('default', 'woman', 'hiphop', 'genz', 'recep', 'grab', 'shopee', 'jnt', 'dhl', 'exec', 'exec_w')
SHEET_PREFIX = {'default': 'staff', 'woman': 'staff_woman', 'hiphop': 'staff_hiphop', 'genz': 'staff_genz',
                'recep': 'staff_recep', 'grab': 'staff_grab', 'shopee': 'staff_shopee', 'jnt': 'staff_jnt',
                'dhl': 'staff_dhl', 'exec': 'staff_exec', 'exec_w': 'staff_exec_w'}
# Tint shirt tetap untuk gaya eksekutif (sut / blazer); dipakai oleh preview, enjin guna nilai sama
STYLE_TINT = {'exec': (0x1f, 0x2a, 0x44), 'exec_w': (0x3b, 0x2a, 0x4a)}
# Tint shirt masa runtime untuk gaya vendor/pelawat (juga dipakai oleh preview)
VENDOR_TINT = {'recep': (0x42, 0x85, 0xf4), 'grab': (0x00, 0xb1, 0x4f), 'shopee': (0xee, 0x4d, 0x2d),
               'jnt': (0xd5, 0x20, 0x2a), 'dhl': (0xff, 0xcc, 0x00)}

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
    # --- role vendor/pelawat (recep, grab, shopee, jnt, dhl) ---
    'white': {0: (206, 212, 222, 255), 1: (238, 241, 246, 255), 2: (255, 255, 255, 255)},   # trim/blaus/logo
    'gblue': {0: (40, 92, 196, 255), 1: (66, 133, 244, 255), 2: (140, 184, 252, 255)},      # lanyard
    'grabbag': {0: (0, 112, 52, 255), 1: (0, 168, 76, 255), 2: (78, 214, 134, 255)},
    'shopeebag': {0: (176, 52, 26, 255), 1: (238, 77, 45, 255), 2: (255, 140, 104, 255)},
    'cardboard': {0: (148, 102, 58, 255), 1: (196, 146, 88, 255), 2: (226, 182, 124, 255)},
    'jnt_red': {0: (150, 18, 28, 255), 1: (213, 32, 42, 255), 2: (244, 92, 96, 255)},
    'dhl_yellow': {0: (214, 160, 0, 255), 1: (255, 204, 0, 255), 2: (255, 232, 118, 255)},
    'dhl_red': {0: (150, 12, 22, 255), 1: (212, 5, 17, 255), 2: (240, 72, 72, 255)},
    # --- role eksekutif (exec, exec_w) ---
    'tie': {0: (140, 20, 30, 255), 1: (200, 36, 46, 255), 2: (240, 96, 96, 255)},
    'trousers': {0: (34, 36, 44, 255), 1: (50, 53, 64, 255), 2: (72, 76, 90, 255)},
    'oxford': {0: (12, 10, 12, 255), 1: (34, 30, 34, 255), 2: (130, 130, 144, 255)},
    'pearl': {1: (226, 222, 210, 255), 2: (255, 255, 248, 255)},
    'pencil': {0: (62, 62, 74, 255), 1: (88, 88, 102, 255), 2: (116, 116, 132, 255)},
    'pumps': {0: (16, 12, 16, 255), 1: (40, 30, 40, 255), 2: (150, 130, 150, 255)},
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
    elif style == 'exec_w':  # rambut paras bahu, hujung melentik ke luar
        for x, sh in ((10, 0), (11, 1), (12, 2), (20, 2), (21, 1), (22, 0)):
            b.put(x, y0 + 11, 'hair', sh)
        for x, sh in ((9, 0), (10, 1), (11, 0), (21, 0), (22, 1), (23, 0)):
            b.put(x, y0 + 12, 'hair', sh)


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
    elif style == 'exec':  # jaket sut: kolar kemeja putih + belahan (vent) di belakang
        for row in range(14):
            for x in range(11, 21):
                b.put(x, yt + row, 'shirt', 2 if x <= 12 else 0 if x >= 19 else 1)
        for x in range(13, 20):
            b.put(x, yt + 1, 'shirt', 0)
        for x in range(14, 19):
            b.put(x, yt, 'white', 1)
        for row in (11, 12, 13):
            b.put(16, yt + row, 'shirt', 0)
    elif style == 'exec_w':  # blazer + skirt pensel
        for row in range(11):
            xs = range(11, 21) if row <= 4 else range(12, 20)
            for x in xs:
                shade = 2 if x <= 12 else 0 if x >= 19 else 1
                if row >= 9:
                    shade = 0
                b.put(x, yt + row, 'shirt', shade)
        for row in range(11, 14):
            for x in range(12, 20):
                b.put(x, yt + row, 'pencil', 0 if row == 11 else 2 if x <= 13 else 0 if x >= 18 else 1)
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
    elif style == 'exec_w':
        back_hair_bob(b, y0)

    return add_outline(b)


# ---- gaya staff vendor/pelawat: recep, grab, shopee, jnt, dhl -------------------------------
# Lapisan shirt ditint masa runtime (warna jenama); cap/uniform ikut tint. Elemen jenama tetap
# (beg, bungkusan, trim, logo) berada dalam lapisan fixed melalui role baru.

VENDOR_STYLES = ('recep', 'grab', 'shopee', 'jnt', 'dhl')
LEGS_ROLE = {'grab': 'pants2', 'shopee': 'pants2', 'jnt': 'pants', 'dhl': 'pants2'}

ARM_RIDER = dict(lx=8, rx=21, w=3, sleeve=4, hand=7, hand_in=0, tl=9, tr=20, k_skin=4, rs=22, skin_from=0.3,
                 shl=(2, 1, 1), shr=(1, 1, 0))
ARM_RECEP = dict(lx=8, rx=21, w=3, sleeve=9, hand=2, hand_in=0, tl=9, tr=20, k_skin=99, rs=22, skin_from=0.85,
                 shl=(2, 1, 1), shr=(1, 1, 0))
for _s in VENDOR_STYLES:
    ARM[_s] = ARM_RECEP if _s == 'recep' else ARM_RIDER
    BACK_ARM[_s] = dict(lx=8, rx=21, w=3, skin_from=99 if _s == 'recep' else 4, shl=(2, 1, 1), shr=(1, 1, 0))


def put_rows(b, x0, y0, rows, mapping):
    """Lukis ascii-art: mapping {aksara: (role, shade)}; '.' = kosong."""
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch in mapping:
                role, sh = mapping[ch]
                b.put(x0 + gx, y0 + gy, role, sh)


GLYPH_G = ["XXX.", "X...", "X.XX", "X..X", "XXX."]   # 'G' stylised (4x5)
GLYPH_G5 = [".XXX.", "X....", "X.XXX", "X...X", ".XXX."]
GLYPH_S = [".XXX", "X...", ".XX.", "...X", "XXX."]    # 'S' stylised (4x5)


# ---- kepala ---------------------------------------------------------------------

def head_recep(b, y0):
    head_shape(b, y0, jaw_dark=False)
    # rambut disisir ke belakang + sanggul di atas
    for x in range(15, 18):
        b.put(x, y0 - 3, 'hair', 2)
    for row in (-2, -1):
        for x in range(14, 19):
            b.put(x, y0 + row, 'hair', 2 if (row == -2 and x <= 16) else 0 if x == 18 else 1)
    for x in range(12, 21):
        b.put(x, y0, 'hair', 2)
    for row in (1, 2):
        for x in range(11, 22):
            b.put(x, y0 + row, 'hair', 2 if (row == 1 and 12 <= x <= 14) else 0 if x in (11, 21) else 1)
    for x in range(11, 15):
        b.put(x, y0 + 3, 'hair', 2 if x <= 12 else 1)
    for x in (20, 21):
        b.put(x, y0 + 3, 'hair', 1)
    for row in (4, 5):
        b.put(11, y0 + row, 'hair', 0)
        b.put(21, y0 + row, 'hair', 0)
    # headset: band melintas atas kepala, cawan di telinga, mic boom ke mulut
    for x in range(12, 21):
        b.put(x, y0, 'cap', 2 if x in (15, 16) else 1)
    b.put(11, y0 + 1, 'cap', 1)
    b.put(21, y0 + 1, 'cap', 1)
    for x0 in (9, 22):
        b.put(x0 + (1 if x0 == 9 else 0), y0 + 2, 'cap', 1)
        b.put(x0 + (1 if x0 == 9 else 0), y0 + 3, 'cap', 1)
        for row in range(4, 8):
            b.put(x0, y0 + row, 'cap', 1)
            b.put(x0 + 1, y0 + row, 'cap', 2 if row == 5 else 1)
    for (x, y) in ((10, 8), (11, 9), (12, 9), (13, 9)):
        b.put(x, y0 + y, 'cap', 1)
    b.put(14, y0 + 8, 'cap', 2)
    b.put(14, y0 + 9, 'cap', 1)
    # muka
    for x in (13, 14, 18, 19):
        b.put(x, y0 + 5, 'eyes')
    b.put(12, y0 + 4, 'eyes')
    b.put(20, y0 + 4, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'lips')


def head_rider(b, y0, style):
    head_shape(b, y0, jaw_dark=(style != 'shopee'))
    if style == 'shopee':  # rambut panjang jatuh di sisi muka, bawah kap
        for row in range(4, 11):
            for x, sh in ((10, 0), (11, 1), (21, 1), (22, 0)):
                if row == 10 and x in (11, 21):
                    continue
                b.put(x, y0 + row, 'hair', sh)
        for x in (10, 22):
            b.put(x, y0 + 11, 'hair', 0)
    # kap (lapisan shirt, ikut tint jenama)
    for x in range(12, 21):
        b.put(x, y0, 'shirt', 2)
    for row in (1, 2):
        for x in range(11, 22):
            b.put(x, y0 + row, 'shirt', 2 if (row == 1 and x in (13, 14)) else 0 if x in (11, 21) else 1)
    # brim (lebih lebar dari kepala)
    for x in range(10, 23):
        b.put(x, y0 + 3, 'shirt', 0 if x in (10, 22) else 2 if x < 13 else 1)
    for x in range(12, 21):
        b.put(x, y0 + 4, 'skin', 0)  # bayang di bawah brim
    if style != 'shopee':
        for row in (4, 5):
            b.put(11, y0 + row, 'hair', 0)
            b.put(21, y0 + row, 'hair', 0)
    # tanda jenama pada kap
    if style == 'grab':
        for x, y in ((15, 1), (16, 1), (17, 1), (15, 2), (17, 2), (16, 2)):
            b.put(x, y0 + y, 'white', 2)
        b.put(16, y0 + 2, 'shirt', 1)
    elif style == 'shopee':
        for x, y in ((15, 1), (16, 1), (16, 2), (17, 2)):
            b.put(x, y0 + y, 'white', 2)
    elif style == 'jnt':
        for x in range(11, 22):
            b.put(x, y0 + 2, 'white', 2 if 12 <= x <= 20 else 0)
    elif style == 'dhl':
        for x in range(11, 22):
            b.put(x, y0 + 2, 'dhl_red', 1)
    # muka
    if style == 'shopee':
        for x in (13, 14, 18, 19):
            b.put(x, y0 + 5, 'eyes')
        for x in (15, 16, 17):
            b.put(x, y0 + 8, 'lips')
    else:
        b.put(14, y0 + 5, 'eyes')
        b.put(18, y0 + 5, 'eyes')
        for x in (15, 16, 17):
            b.put(x, y0 + 8, 'mouth')
        if style == 'dhl':  # janggut tipis
            for x in (13, 14, 18, 19):
                b.put(x, y0 + 9, 'hair', 0)
            for x in (15, 16, 17):
                b.put(x, y0 + 9, 'hair', 0)
            for x in (15, 16, 17):
                b.put(x, y0 + 8, 'mouth')


# ---- badan ----------------------------------------------------------------------

def torso_recep(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    # blazer (shirt) bahu lebar, pinggang kecil
    for row in range(11):
        xs = range(11, 21) if row <= 4 else range(12, 20)
        for x in xs:
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            if row >= 9:
                shade = 0 if x >= 14 else 1
            b.put(x, yt + row, 'shirt', shade)
    # kolar blaus putih + V
    for x in (15, 16, 17):
        b.put(x, yt, 'skin', 1)
    b.put(14, yt, 'white', 2)
    b.put(18, yt, 'white', 1)
    for x in (14, 15, 17, 18):
        b.put(x, yt + 1, 'white', 2 if x < 16 else 1)
    b.put(16, yt + 1, 'skin', 1)
    for x in (15, 16, 17):
        b.put(x, yt + 2, 'white', 2 if x == 15 else 1)
    b.put(16, yt + 3, 'white', 1)
    # lapel blazer gelap
    for (x, y) in ((13, 1), (13, 2), (14, 3), (14, 4), (15, 4), (19, 1), (18, 2), (18, 3), (17, 4)):
        b.put(x, yt + y, 'shirt', 0)
    # lanyard biru + tag nama putih
    for (x, y) in ((14, 2), (15, 3), (15, 4), (16, 5)):
        b.put(x, yt + y, 'gblue', 1)
    for (x, y) in ((18, 3), (17, 4), (17, 5)):
        b.put(x, yt + y, 'gblue', 1)
    for y in (6, 7, 8):
        for x in (15, 16, 17):
            b.put(x, yt + y, 'white', 2 if y < 8 else 0)
    b.put(15, yt + 6, 'gblue', 1)
    b.put(16, yt + 7, 'gblue', 2)
    # skirt pensil gelap (role pants2) hingga atas lutut
    last = 13 if seated else 19
    for row in range(11, last + 1):
        x0, x1 = (12, 19) if row <= 12 else (11, 20)
        for x in range(x0, x1 + 1):
            shade = 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1
            if row == 11 or row == last:
                shade = 0
            b.put(x, yt + row, 'pants2', shade)


def torso_rider(b, yt, seated, style):
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
    b.put(14, yt, 'shirt', 2)
    b.put(18, yt, 'shirt', 2)
    b.put(14, yt + 1, 'shirt', 2)
    b.put(18, yt + 1, 'shirt', 2)
    if style == 'grab':
        put_rows(b, 14, yt + 4, GLYPH_G5, {'X': ('white', 2)})
    elif style == 'shopee':
        put_rows(b, 14, yt + 4, GLYPH_S, {'X': ('white', 2)})
        for x in range(11, 21):
            b.put(x, yt + 12, 'white', 1)
    elif style == 'jnt':
        for x in range(11, 21):
            b.put(x, yt + 6, 'white', 2 if x < 19 else 1)
            b.put(x, yt + 7, 'white', 1 if x < 19 else 0)
        for x in (14, 18):
            b.put(x, yt, 'white', 2)
    elif style == 'dhl':
        for x in range(11, 21):
            b.put(x, yt + 5, 'dhl_red', 1)
            b.put(x, yt + 6, 'dhl_red', 0 if x >= 19 else 1)
        for x in (14, 18):
            b.put(x, yt, 'dhl_red', 1)


def legs_rider(role):
    def legs(b, lx, rx, llift, rlift):
        for x0, off, lift, shades in ((11, lx, llift, (2, 1, 1, 1, 0)), (16, rx, rlift, (1, 1, 1, 1, 0))):
            bottom = 43 - lift
            for y in range(32, bottom + 1):
                for i in range(5):
                    b.put(x0 + off + i, y, role, shades[i])
            for y in range(bottom + 1, bottom + 4):
                for i in range(-1 if x0 == 11 else 0, 6 if x0 == 16 else 5):
                    b.put(x0 + off + i, y, 'shoes', 0 if y == bottom + 3 else 1)
    return legs


def legs_recep(b, lx, rx, llift, rlift):
    legs_woman(b, lx, rx, llift, rlift)


for _s in VENDOR_STYLES:
    HEAD[_s] = head_recep if _s == 'recep' else (lambda b, y0, s=_s: head_rider(b, y0, s))
    TORSO[_s] = torso_recep if _s == 'recep' else (lambda b, yt, seated, s=_s: torso_rider(b, yt, seated, s))
    LEGS[_s] = legs_recep if _s == 'recep' else legs_rider(LEGS_ROLE[_s])


# ---- gaya eksekutif: exec (sut + tali leher), exec_w (blazer + skirt pensel) ---------------------
# Jaket/blazer = lapisan shirt (tint runtime 0x1f2a44 / 0x3b2a4a). Kolar putih, tali leher merah,
# seluar, kasut, mutiara dan skirt berada dalam lapisan fixed.

def head_exec(b, y0):
    head_shape(b, y0)
    # rambut pendek kemas, belah tepi (garis belah pada x=14), sideburn pendek
    for x in range(12, 21):
        b.put(x, y0, 'hair', 0 if x == 14 else 2 if 15 <= x <= 18 else 1)
    for x in range(11, 22):
        b.put(x, y0 + 1, 'hair', 0 if x in (11, 14, 21) else 2 if 16 <= x <= 19 else 1)
        b.put(x, y0 + 2, 'hair', 0 if x in (11, 21) else 2 if x in (15, 16) else 1)
    for x, sh in ((11, 0), (12, 1), (13, 1), (20, 1), (21, 0)):
        b.put(x, y0 + 3, 'hair', sh)
    b.put(11, y0 + 4, 'hair', 0)
    b.put(21, y0 + 4, 'hair', 0)
    for x in (13, 14, 18, 19):  # kening
        b.put(x, y0 + 4, 'hair', 0)
    b.put(14, y0 + 5, 'eyes')
    b.put(18, y0 + 5, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'mouth')


def head_exec_w(b, y0):
    head_shape(b, y0, jaw_dark=False)
    # rambut paras bahu, belah tepi kanan (x=17), bang disisir ke kiri
    for x in range(12, 21):
        b.put(x, y0, 'hair', 0 if x == 17 else 2 if x <= 16 else 1)
    for row in (1, 2):
        for x in range(10, 23):
            if x in (10, 22):
                sh = 0
            elif row == 1:
                sh = 0 if x == 17 else 2 if 12 <= x <= 16 else 1
            else:
                sh = 2 if 13 <= x <= 15 else 1
            b.put(x, y0 + row, 'hair', sh)
    for x in range(11, 18):
        b.put(x, y0 + 3, 'hair', 2 if x <= 13 else 1)
    for x in (20, 21):
        b.put(x, y0 + 3, 'hair', 1)
    for x, sh in ((10, 0), (11, 1), (12, 1), (13, 1), (20, 1), (21, 1), (22, 0)):
        b.put(x, y0 + 4, 'hair', sh)
    for row in range(5, 11):
        for x, sh in ((10, 0), (11, 1), (12, 2), (20, 2), (21, 1), (22, 0)):
            b.put(x, y0 + row, 'hair', sh)
    for x in (13, 14, 18, 19):
        b.put(x, y0 + 5, 'eyes')
    for x in (15, 16, 17):
        b.put(x, y0 + 8, 'lips')
    b.put(12, y0 + 8, 'pearl', 2)  # anting-anting mutiara
    b.put(20, y0 + 8, 'pearl', 1)


def torso_exec(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    for row in range(14):
        for x in range(11, 21):
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            if row >= 12:
                shade = 0
            b.put(x, yt + row, 'shirt', shade)
    # kemeja putih dalam bukaan V
    for x, y, sh in ((14, 0, 2), (15, 0, 2), (17, 0, 1), (18, 0, 1), (15, 1, 2), (17, 1, 1), (15, 2, 2), (17, 2, 1),
                     (15, 3, 2), (17, 3, 1)):
        b.put(x, yt + y, 'white', sh)
    # tali leher merah
    for y, sh in ((0, 1), (1, 2), (2, 1), (3, 1), (4, 1), (5, 0)):
        b.put(16, yt + y, 'tie', sh)
    # lapel (garis gelap + kilau)
    for x, y in ((13, 0), (14, 1), (14, 2), (14, 3), (15, 4), (19, 0), (18, 1), (18, 2), (18, 3), (17, 4)):
        b.put(x, yt + y, 'shirt', 0)
    b.put(13, yt + 1, 'shirt', 2)
    b.put(13, yt + 2, 'shirt', 2)
    b.put(18, yt + 5, 'white', 2)  # sapu tangan poket
    b.put(19, yt + 5, 'white', 1)
    b.put(16, yt + 8, 'shirt', 0)  # butang
    if not seated:
        b.put(16, yt + 11, 'shirt', 0)


def torso_exec_w(b, yt, seated):
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    for row in range(11):
        xs = range(11, 21) if row <= 4 else range(12, 20)
        for x in xs:
            shade = 2 if x <= 12 else 0 if x >= 19 else 1
            if row >= 9:
                shade = 0 if x >= 14 else 1
            b.put(x, yt + row, 'shirt', shade)
    # blaus putih + rantai mutiara
    for x, y, role, sh in ((14, 0, 'white', 2), (15, 0, 'skin', 1), (16, 0, 'skin', 1), (17, 0, 'skin', 1),
                           (18, 0, 'white', 1), (14, 1, 'white', 2), (15, 1, 'pearl', 2), (16, 1, 'skin', 1),
                           (17, 1, 'pearl', 1), (18, 1, 'white', 1), (15, 2, 'white', 2), (16, 2, 'pearl', 2),
                           (17, 2, 'white', 1), (16, 3, 'white', 1)):
        b.put(x, yt + y, role, sh)
    for x, y in ((13, 1), (19, 1), (14, 2), (18, 2), (15, 3), (17, 3), (16, 4)):
        b.put(x, yt + y, 'shirt', 0)
    b.put(13, yt + 2, 'shirt', 2)
    b.put(16, yt + 7, 'shirt', 0)  # butang
    # skirt pensel kelabu (fixed) hingga lutut, mengecil di bawah
    last = 13 if seated else 18
    for row in range(11, last + 1):
        x0, x1 = (12, 19) if row <= 16 else (13, 18)
        for x in range(x0, x1 + 1):
            shade = 2 if x <= x0 + 1 else 0 if x >= x1 else 1
            if row == last and not seated:
                shade = 0
            b.put(x, yt + row, 'pencil', shade)


def legs_exec(b, lx, rx, llift, rlift):
    for x0, off, lift, shades in ((11, lx, llift, (2, 1, 1, 1, 0)), (16, rx, rlift, (1, 1, 1, 1, 0))):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            for i in range(5):
                b.put(x0 + off + i, y, 'trousers', shades[i])
        left = x0 == 11
        for y in range(bottom + 1, bottom + 4):
            for i in range(-1 if left else 0, 6 if not left else 5):
                b.put(x0 + off + i, y, 'oxford', 0 if y == bottom + 3 else 1)
        b.put(x0 + off + (0 if left else 4), bottom + 2, 'oxford', 2)  # kilat kasut


def legs_exec_w(b, lx, rx, llift, rlift):
    for x0, off, lift, shades in ((12, lx, llift, (2, 1, 0)), (17, rx, rlift, (2, 1, 0))):
        bottom = 43 - lift
        for y in range(32, bottom + 1):
            for i in range(3):
                b.put(x0 + off + i, y, 'skin', shades[i] if y < bottom - 1 else 1)
        left = x0 == 12
        for x in range(x0, x0 + 3):
            b.put(x + off, bottom + 1, 'pumps', 1)
        lo, hi = (x0 - 1, x0 + 2) if left else (x0, x0 + 3)
        for x in range(lo, hi + 1):
            b.put(x + off, bottom + 2, 'pumps', 1)
        b.put((lo if left else hi) + off, bottom + 2, 'pumps', 2)
        for x in range(lo + 1, hi):
            b.put(x + off, bottom + 3, 'pumps', 0)


def back_hair_bob(b, y0):
    """Rambut paras bahu exec_w dari belakang (lukis selepas badan)."""
    for row in range(9, 14):
        x0, x1 = (11, 21) if row <= 11 else (10, 22)
        for x in range(x0, x1 + 1):
            sh = 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1
            if row == 13:
                sh = 0
            b.put(x, y0 + row, 'hair', sh)


HEAD.update({'exec': head_exec, 'exec_w': head_exec_w})
TORSO.update({'exec': torso_exec, 'exec_w': torso_exec_w})
LEGS.update({'exec': legs_exec, 'exec_w': legs_exec_w})
BACK_HEAD.update({'exec': back_head_default, 'exec_w': back_head_woman})
for _s in ('exec', 'exec_w'):
    ARM[_s] = dict(ARM['default'])
    BACK_ARM[_s] = dict(BACK_ARM['default'])


# ---- barang bawaan ----------------------------------------------------------------

def bag_item(b, x0, y0, w, h, role, glyph, handle=True):
    """Beg penghantar berinsulasi: lid + badan, tanda putih di tengah, pemegang di atas."""
    if handle:
        for x in range(x0 + 2, x0 + w - 2):
            b.put(x, y0 - 2, 'cap', 1)
        b.put(x0 + 2, y0 - 1, 'cap', 1)
        b.put(x0 + w - 3, y0 - 1, 'cap', 1)
    for y in range(h):
        for x in range(w):
            sh = 1
            if y == 0:
                sh = 2
            elif y == 2 or y == h - 1 or x == w - 1:
                sh = 0
            elif x == 0:
                sh = 2
            b.put(x0 + x, y0 + y, role, sh)
    gx = x0 + (w - len(glyph[0])) // 2
    put_rows(b, gx, y0 + 3, glyph, {'X': ('white', 2)})
    b.put(x0 + w // 2, y0 + 1, 'white', 1)  # kepala zip


def parcel_item(b, x0, y0, w, h, kind, handle=True):
    """Kotak bungkusan: kind = 'jnt' (kadbod + jalur merah) / 'dhl' (kuning + jalur merah)."""
    body, band = ('cardboard', 'jnt_red') if kind == 'jnt' else ('dhl_yellow', 'dhl_red')
    if handle:
        for x in range(x0 + 2, x0 + w - 2):
            b.put(x, y0 - 2, 'cap', 1)
        b.put(x0 + 2, y0 - 1, 'cap', 1)
        b.put(x0 + w - 3, y0 - 1, 'cap', 1)
    for y in range(h):
        for x in range(w):
            sh = 1
            if y == 0:
                sh = 2
            elif y == h - 1 or x == w - 1:
                sh = 0
            elif x == 0:
                sh = 2
            b.put(x0 + x, y0 + y, body, sh)
    for x in range(w):
        b.put(x0 + x, y0 + 1, body, 0)  # garis lipatan penutup
    if kind == 'jnt':
        cx = x0 + w // 2 - 1
        for y in range(h):
            for dx in (0, 1):
                b.put(cx + dx, y0 + y, band, 2 if dx == 0 else 1)
        for y in (3, 4):
            for x in range(x0 + w - 4, x0 + w - 1):
                b.put(x, y0 + y, 'white', 2)
        b.put(x0 + w - 3, y0 + 4, band, 1)
    else:
        my = y0 + h // 2 - 1
        for y in (0, 1):
            for x in range(w):
                b.put(x0 + x, my + y, band, 1 if y == 0 else 0)
        for y in (2, 3):
            for x in range(x0 + 1, x0 + 4):
                b.put(x, y0 + y, 'white', 2)


def item_ring(b, x0, y0, w, h):
    """Garis luar gelap di sekeliling barang (hanya pada piksel kosong) supaya nampak di atas baju sewarna."""
    for x in range(x0 - 1, x0 + w + 1):
        for y in (y0 - 1, y0 + h):
            if (x, y) not in b.px:
                b.put(x, y, 'outline', 1)
    for y in range(y0, y0 + h):
        for x in (x0 - 1, x0 + w):
            if (x, y) not in b.px:
                b.put(x, y, 'outline', 1)


def item_for(b, style, x0, y0, w, h, handle=True):
    if style in ('grab', 'shopee', 'jnt', 'dhl'):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                b.px.pop((x, y), None)
        item_ring(b, x0, y0, w, h)
    _item_for(b, style, x0, y0, w, h, handle)


def _item_for(b, style, x0, y0, w, h, handle=True):
    if style == 'grab':
        bag_item(b, x0, y0, w, h, 'grabbag', GLYPH_G, handle)
    elif style == 'shopee':
        bag_item(b, x0, y0, w, h, 'shopeebag', GLYPH_S, handle)
    elif style == 'jnt':
        parcel_item(b, x0, y0, w, h, 'jnt', handle)
    elif style == 'dhl':
        parcel_item(b, x0, y0, w, h, 'dhl', handle)


def trim_sleeves(b, yt, style, A, al=0, ar=0):
    """Cuff trim pada hujung lengan baju (jnt putih, dhl merah)."""
    role = {'jnt': 'white', 'dhl': 'dhl_red'}.get(style)
    if not role:
        return
    for x0, off in ((A['lx'], al), (A['rx'], ar)):
        for i in range(A['w']):
            b.put(x0 + i, yt + A['sleeve'] + off, role, 2 if i == 0 else 1)


def hold_arms(b, yt, style, phase):
    """Dua tangan ke hadapan memegang barang di depan dada (frame 10-11)."""
    A = ARM[style]
    for x0, sh in ((A['lx'], A['shl']), (A['rx'], A['shr'])):
        for row in range(4):
            for i in range(A['w']):
                b.put(x0 + i, yt + 1 + row, 'shirt', sh[i])
    up = phase
    stroke(b, (9, yt + 5), (10, yt + 9 - up), 3, 'skin', (1,))
    stroke(b, (22, yt + 5), (21, yt + 9 - up), 3, 'skin', (1,))
    return up


def figure_vendor(style, dy=0, seated=False, lx=0, rx=0, llift=0, rlift=0, al=0, ar=0, typing=None, pose=None,
                  hold=None, carry=False):
    b = Buf()
    y0 = 6 + dy
    yt = y0 + 12
    A = ARM[style]
    if not seated:
        LEGS[style](b, lx, rx, llift, rlift)
    HEAD[style](b, y0)
    TORSO[style](b, yt, seated)
    if hold is not None:
        if style == 'recep':
            hang_arm(b, yt, A['lx'], 0, A['shl'], A)
            for row in range(1, 4):
                for i in range(A['w']):
                    b.put(A['rx'] + i, yt + row, 'shirt', A['shr'][i])
            sx, sy = A['rs'], yt + 2
            bent_arm(b, (sx, sy), (sx + 3, sy + 3 - hold), (sx + 6, yt + 6 - 2 * hold), A)
            # kad/dokumen putih dihulur
            for gy in range(5):
                for gx in range(4):
                    b.put(sx + 5 + gx, yt + 1 - 2 * hold + gy, 'white', 2 if gy == 0 or gx == 0 else 1 if gx < 3 else 0)
            b.put(sx + 6, yt + 3 - 2 * hold, 'gblue', 1)
            b.put(sx + 7, yt + 3 - 2 * hold, 'gblue', 1)
        else:
            up = hold_arms(b, yt, style, hold)
            item_for(b, style, 10, yt + 9 - up, 12, 9, handle=False)
            # tangan menggenggam sisi barang
            for y in (yt + 11 - up, yt + 12 - up, yt + 13 - up):
                for x in (9, 22):
                    b.put(x, y, 'skin', 1)
                b.put(10 if y != yt + 13 - up else 9, y, 'skin', 2 if False else 1)
                b.put(21 if y != yt + 13 - up else 22, y, 'skin', 1)
            trim_sleeves(b, yt, style, dict(A, sleeve=4))
    elif pose:
        hang_arm(b, yt, A['lx'], 0, A['shl'], A)
        pose_arm(b, yt, pose, A)
        trim_sleeves(b, yt, style, A)
    elif typing is None:
        hang_arm(b, yt, A['lx'], al, A['shl'], A)
        hang_arm(b, yt, A['rx'], 0 if carry else ar, A['shr'], A)
        if style != 'recep':
            trim_sleeves(b, yt, style, A, al, 0 if carry else ar)
        if carry and style != 'recep':
            item_for(b, style, 22, yt + 14, 9, 10)
    else:
        typing_arms(b, yt, typing, A)
    return add_outline(b)


def back_head_vendor(b, y0, style):
    if style == 'recep':
        for x in range(15, 18):
            b.put(x, y0 - 3, 'hair', 2)
        for row in (-2, -1):
            for x in range(14, 19):
                b.put(x, y0 + row, 'hair', 2 if (row == -2 and x <= 16) else 0 if x == 18 else 1)
        for row in range(10):
            x0, x1 = (12, 20) if row in (0, 9) else (11, 21)
            for x in range(x0, x1 + 1):
                b.put(x, y0 + row, 'hair', 2 if row <= 2 else 1 if row <= 6 else 0)
        for x in range(12, 21):
            b.put(x, y0, 'cap', 2 if x in (15, 16) else 1)
        for x0 in (9, 22):
            for row in range(3, 8):
                b.put(x0, y0 + row, 'cap', 1)
                b.put(x0 + 1, y0 + row, 'cap', 1 if row != 5 else 2)
        for x in (14, 15, 16, 17, 18):
            b.put(x, y0 + 10, 'skin', 0)
        return
    for row in range(11):
        x0, x1 = (12, 20) if row in (0, 9) else (13, 19) if row == 10 else (11, 21)
        for x in range(x0, x1 + 1):
            if row <= 4:
                b.put(x, y0 + row, 'shirt', 2 if (row == 1 and x in (13, 14)) else 0 if x in (11, 21) else 1)
            else:
                b.put(x, y0 + row, 'hair', 1 if row <= 7 else 0)
    for x in range(14, 19):
        b.put(x, y0 + 5, 'shirt', 0)  # strap kap
    if style == 'shopee':  # rambut panjang jatuh ke belakang
        for row in range(8, 17):
            for x in range(12, 21):
                b.put(x, y0 + row, 'hair', 2 if x <= 13 else 0 if x >= 19 else 1)
    else:
        for x in (14, 15, 16, 17, 18):
            b.put(x, y0 + 10, 'skin', 0)
    if style == 'jnt':
        for x in range(11, 22):
            b.put(x, y0 + 4, 'white', 1)
    elif style == 'dhl':
        for x in range(11, 22):
            b.put(x, y0 + 4, 'dhl_red', 1)


def figure_back_vendor(typing=0, style='grab'):
    b = Buf()
    y0 = 10
    back_head_vendor(b, y0, style)
    yt = y0 + 12
    for x in (15, 16, 17):
        b.put(x, yt - 1, 'skin', 0)
    if style == 'recep':
        for row in range(11):
            xs = range(11, 21) if row <= 4 else range(12, 20)
            for x in xs:
                shade = 2 if x <= 12 else 0 if x >= 19 else 1
                if row >= 9:
                    shade = 0
                b.put(x, yt + row, 'shirt', shade)
        for row in range(11, 14):
            x0, x1 = (12, 19)
            for x in range(x0, x1 + 1):
                b.put(x, yt + row, 'pants2', 0 if row == 11 else 2 if x <= x0 + 1 else 0 if x >= x1 - 1 else 1)
    else:
        for row in range(14):
            for x in range(11, 21):
                b.put(x, yt + row, 'shirt', 2 if x <= 12 else 0 if x >= 19 else 1)
        for x in range(13, 20):
            b.put(x, yt, 'shirt', 0)
            b.put(x, yt + 1, 'shirt', 0)
        for x in range(14, 19):
            b.put(x, yt + 2, 'shirt', 0)
    A = BACK_ARM[style]
    for side, x0 in ((0, A['lx']), (1, A['rx'])):
        lift = (typing + side) % 2
        shades = A['shl'] if side == 0 else A['shr']
        for row in range(7):
            skin = row >= A['skin_from']
            for i in range(A['w']):
                b.put(x0 + i, yt + 1 + row - lift, 'skin' if skin else 'shirt', 1 if skin else shades[i])
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


def vendor_frames():
    """Frame untuk gaya vendor: sama seperti FRAMES, tetapi 0-5 membawa barang & 10-11 = hulur/pegang ke depan."""
    out = []
    for i, f in enumerate(FRAMES):
        f = dict(f)
        if i < 6:
            f['carry'] = True
        elif i in (10, 11):
            f = dict(hold=i - 10)
        out.append(f)
    return out


def staff_sheets(style='default'):
    """Pulangkan {fixed, skin, hair, shirt: Image 512x48} untuk satu style."""
    sheets = {name: Image.new('RGBA', (FW * len(FRAMES), FH), (0, 0, 0, 0)) for name in ('fixed', 'skin', 'hair', 'shirt')}
    vendor = style in VENDOR_STYLES
    for index, pose in enumerate(vendor_frames() if vendor else FRAMES):
        if pose.get('back'):
            buf = figure_back_vendor(pose['typing'], style) if vendor else figure_back(pose['typing'], style)
        else:
            buf = figure_vendor(style, **pose) if vendor else figure(style=style, **pose)
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

def wall_door():
    """Pintu masuk pejabat (dua daun kaca, bingkai biru Google) ~2 tile lebar. Lukis rata 56x100, kemudian di-shear."""
    img, d = new(56, 100)
    steel, glass_t, glass_b = (200, 206, 216, 255), (200, 228, 252), (150, 196, 242)
    d.rectangle([0, 0, 55, 99], fill=G_BLUE, outline=OL)           # bingkai
    d.line([(1, 1), (54, 1)], fill=shade(G_BLUE, 1.3))
    d.rectangle([3, 5, 52, 93], fill=(236, 240, 246, 255), outline=OL)  # alur daun pintu
    for x0 in (4, 29):                                              # dua daun
        x1 = x0 + 22
        d.rectangle([x0, 6, x1, 92], fill=(248, 250, 252, 255), outline=(150, 160, 176, 255))
        for y in range(8, 70):                                      # kaca: biru muda -> lebih gelap
            t = (y - 8) / 62
            col = tuple(int(glass_t[i] + (glass_b[i] - glass_t[i]) * t) for i in range(3)) + (255,)
            d.line([(x0 + 2, y), (x1 - 2, y)], fill=col)
        d.rectangle([x0 + 1, 7, x1 - 1, 70], outline=shade(G_BLUE, 0.9))
        for k in range(3):                                          # kilauan serong
            d.line([(x0 + 4 + k, 30 - k), (x0 + 12 + k, 12 - k)], fill=(255, 255, 255, 255))
        d.line([(x0 + 14, 42), (x0 + 19, 32)], fill=(236, 246, 255, 255))
        d.rectangle([x0 + 1, 72, x1 - 1, 91], fill=(228, 232, 240, 255), outline=(150, 160, 176, 255))  # panel bawah
        d.rectangle([x0 + 3, 76, x1 - 3, 87], outline=(190, 198, 212, 255))
        d.line([(x0 + 3, 77), (x1 - 3, 77)], fill=(255, 255, 255, 255))
    d.rectangle([26, 5, 29, 93], fill=G_BLUE, outline=OL)           # tiang tengah
    d.line([(27, 7), (27, 91)], fill=shade(G_BLUE, 1.25))
    for hx in (22, 32):                                             # pemegang bar keluli
        d.rectangle([hx, 40, hx + 1, 62], fill=steel, outline=OL)
        d.line([(hx, 42), (hx, 60)], fill=(255, 255, 255, 255))
    # tanda OPEN kecil pada kaca daun kanan
    d.rectangle([33, 13, 50, 22], fill=(255, 255, 255, 255), outline=OL)
    d.rectangle([34, 14, 49, 21], fill=G_GREEN)
    open_glyphs = {'O': ["XXX", "X.X", "X.X", "X.X", "XXX"], 'P': ["XXX", "X.X", "XXX", "X..", "X.."],
                   'E': ["XXX", "X..", "XX.", "X..", "XXX"], 'N': ["XX.", "X.X", "X.X", "X.X", "X.X"]}
    for i, ch in enumerate('OPEN'):
        for gy, row in enumerate(open_glyphs[ch]):
            for gx, c in enumerate(row):
                if c == 'X':
                    d.point((35 + i * 4 + gx, 15 + gy), fill=(255, 255, 255, 255))
    d.line([(41, 7), (41, 12)], fill=OL)                            # gantung
    # ambang (threshold)
    d.rectangle([0, 94, 55, 99], fill=(214, 218, 224, 255), outline=OL)
    d.line([(2, 96), (53, 96)], fill=(255, 255, 255, 255))
    return img


def counter_parcels():
    """Longgokan barang hantaran di atas kaunter resepsi (56x56, bahagian bawah 16px = kotak kaunter, dibiarkan kosong)."""
    OFF = 12
    img, d = new(56, 56)

    def block(bx, by, hw, h, top, left, right, hi=None):
        sbox(d, bx, by + OFF, hw, h, top, left, right, hi)

    def band(bx, by, hw, h, col, top_col, wd=2):
        by += OFF
        hh = hw // 2
        mx = bx + hw // 2 - 1
        for x in range(mx, mx + wd):  # jalur menegak pada muka kanan
            d.line([(x, by - h - (x - bx) // 2), (x, by - (x - bx) // 2 - 1)], fill=col)
        m1 = (bx - hw // 2, by - h - (hw + hh) // 2)
        m2 = (bx + hw // 2, by - h - hh // 2)
        d.line([m1, m2], fill=top_col, width=2)

    def label(bx, by, hw, h, rows, colors, fx0, fy0):
        fl, _ = new(len(rows[0]), len(rows))
        put_flat(fl, rows, colors)
        face_paste(img, fl, bx, by + OFF, hw, h, 'L', fx0, fy0)

    def put_flat(fl, rows, colors):
        for gy, row in enumerate(rows):
            for gx, ch in enumerate(row):
                if ch in colors:
                    fl.putpixel((gx, gy), colors[ch])

    WHT, RED = (255, 255, 255, 255), (213, 32, 42, 255)
    # beg oren (belakang)
    OR, ORl, ORr = (238, 77, 45, 255), (226, 66, 34, 255), (176, 52, 26, 255)
    block(30, 17, 7, 12, (255, 150, 112, 255), OR, ORr, (255, 190, 160, 255))
    d.rectangle([28, 17 + OFF - 12 - 5, 32, 17 + OFF - 12 - 4], fill=(40, 40, 46, 255))  # pemegang
    label(30, 17, 7, 12, [".XX.", "X...", ".XX.", "...X", "XXX."], {'X': WHT}, 1, 4)
    # kotak J&T (kadbod + jalur merah + label)
    block(17, 22, 9, 9, (232, 190, 130, 255), (206, 154, 92, 255), (160, 112, 64, 255), (246, 214, 164, 255))
    band(17, 22, 9, 9, RED, RED)
    label(17, 22, 9, 9, ["XXXX", "XXXX", "X..X"], {'X': WHT}, 1, 3)
    # kotak DHL (kuning + jalur merah)
    YL = (255, 204, 0, 255)
    block(42, 21, 8, 8, (255, 232, 118, 255), YL, (214, 160, 0, 255), (255, 244, 170, 255))
    band(42, 21, 8, 8, (212, 5, 17, 255), (212, 5, 17, 255))
    label(42, 21, 8, 8, ["XXX", "XXX"], {'X': WHT}, 1, 2)
    # beg hijau (hadapan)
    block(29, 27, 7, 11, (110, 220, 150, 255), (0, 168, 76, 255), (0, 112, 52, 255), (170, 244, 198, 255))
    d.rectangle([27, 27 + OFF - 11 - 5, 31, 27 + OFF - 11 - 4], fill=(40, 40, 46, 255))
    label(29, 27, 7, 11, ["XXX.", "X...", "X.XX", "X..X", "XXX."], {'X': WHT}, 1, 3)
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


# ---------------------------------------------------------------- kiosk berjenama (pantri)
# Peti isometrik bersaiz bebas (sbox) + logo rata yang di-shear ke muka kiri/kanan (face_paste).

def sbox(d, bx, by, hw, h, top, left, right, hi=None):
    """Peti isometrik: bucu bawah (bx, by), separuh-lebar hw (muka condong 1:2), tinggi h."""
    hh = hw // 2
    d.polygon([(bx - hw, by - hh - h), (bx, by - h), (bx, by), (bx - hw, by - hh)], fill=left, outline=OL)
    d.polygon([(bx + hw, by - hh - h), (bx, by - h), (bx, by), (bx + hw, by - hh)], fill=right, outline=OL)
    d.polygon([(bx, by - h - hw), (bx + hw, by - h - hh), (bx, by - h), (bx - hw, by - h - hh)], fill=top, outline=OL)
    if hi:
        d.line([(bx - hw + 2, by - h - hh), (bx, by - h - hw + 2), (bx + hw - 2, by - h - hh)], fill=hi)


def face_paste(img, flat, bx, by, hw, h, face, fx0, fy0):
    """Tampal imej rata `flat` pada muka sbox. fx0/fy0 = ofset dari bucu atas-luar muka. Shear 1px/2px."""
    hh = hw // 2
    px = flat.load()
    for fx in range(flat.width):
        u = fx0 + fx
        for fy in range(flat.height):
            c = px[fx, fy]
            if not c[3]:
                continue
            if face == 'L':
                x, y = bx - hw + u, by - hh - h + u // 2 + fy0 + fy
            else:
                x, y = bx + u, by - h - u // 2 + fy0 + fy
            img.putpixel((x, y), c)


def flat_rows(flat, x0, y0, rows, color):
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch == 'X':
                flat.putpixel((x0 + gx, y0 + gy), color)


SB_GREEN = (0, 112, 74, 255)
SB_DARK = (30, 57, 50, 255)
WHITE_C = (255, 255, 255, 255)


def shade_img(src, f):
    out = src.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (int(r * f), int(g * f), int(b * f), a)
    return out


def starbucks_logo(size=17):
    """Logo bulat rata: cincin hijau luar, cincin putih, cakera hijau, siren putih ringkas."""
    fl, d = new(size, size)
    r = size - 1
    d.ellipse([0, 0, r, r], fill=SB_GREEN)
    d.ellipse([1, 1, r - 1, r - 1], fill=WHITE_C)
    d.ellipse([2, 2, r - 2, r - 2], fill=SB_GREEN)
    siren = ["....X....",
             "...XXX...",
             "..XXXXX..",
             "..X.X.X..",
             ".XXXXXXX.",
             "X.XXXXX.X",
             "XX.XXX.XX",
             ".X..X..X.",
             "...XXX..."]
    o = (size - 9) // 2
    flat_rows(fl, o, o, siren, WHITE_C)
    return fl


def machine_starbucks():
    hs = 70
    img, d = new(56, hs)
    cx, cy = box(d, hs, 12, (244, 246, 244, 255), SB_DARK, shade(SB_DARK, 0.7), (255, 255, 255, 255))
    d.line([left_pt(cy, 12, 1, 8), left_pt(cy, 12, 27, 8)], fill=SB_GREEN)
    d.line([(30, cy + 8 + 1), (54, cy - 7 + 1)], fill=shade(SB_GREEN, 0.75))
    ty = cy - 12  # pusat muka atas kaunter
    hw, h = 20, 26
    bx, by = 28, ty + 4
    sbox(d, bx, by, hw, h, (236, 240, 244, 255), (222, 228, 234, 255), (170, 178, 188, 255), (255, 255, 255, 255))
    # trim hijau (apron) atas & bawah pada kedua-dua muka
    for face, k in (('L', 1.0), ('R', 0.75)):
        fl, fd = new(hw - 1, 1)
        fd.line([(0, 0), (hw - 2, 0)], fill=shade(SB_GREEN, k))
        for fy in (1, 2, h - 3, h - 2):
            face_paste(img, fl, bx, by, hw, h, face, 1, fy)
    logo = starbucks_logo(17)
    face_paste(img, logo, bx, by, hw, h, 'L', 1, 5)
    face_paste(img, shade_img(logo, 0.78), bx, by, hw, h, 'R', 1, 5)
    # hopper biji kopi di atas
    sbox(d, bx, by - h - hw // 2 + 4, 7, 6, (110, 70, 44, 255), (84, 52, 32, 255), (60, 36, 22, 255), (160, 110, 74, 255))
    # dulang titis hitam di hadapan + cawan hijau-putih
    sbox(d, 28, ty + 13, 12, 3, (50, 50, 58, 255), (32, 32, 38, 255), (20, 20, 26, 255), (96, 96, 108, 255))
    d.rectangle([33, ty + 1, 37, ty + 7], fill=WHITE_C, outline=OL)
    d.rectangle([34, ty + 3, 36, ty + 4], fill=SB_GREEN)
    # muncung wap keluli (kanan) + wap
    d.rectangle([51, ty - 9, 52, ty + 1], fill=(200, 206, 214, 255), outline=OL)
    d.point((51, ty + 2), fill=OL)
    d.point((52, ty + 2), fill=OL)
    for (x, y) in ((51, ty - 12), (52, ty - 15), (50, ty - 18), (51, ty - 21)):
        d.point((x, y), fill=(252, 252, 254, 255))
        d.point((x + 1, y), fill=(252, 252, 254, 255))
        d.point((x, y + 1), fill=(210, 222, 232, 255))
    return img


def machine_zus():
    hs = 72
    img, d = new(56, hs)
    NAVY, NAVY_L, NAVY_R = (14, 42, 96, 255), (20, 58, 124, 255), (10, 30, 72, 255)
    YEL = (255, 204, 0, 255)
    cx, cy = box(d, hs, 12, (240, 242, 246, 255), (228, 232, 240, 255), (192, 198, 210, 255), (255, 255, 255, 255))
    d.line([left_pt(cy, 12, 1, 8), left_pt(cy, 12, 27, 8)], fill=YEL)
    d.line([(30, cy + 8 + 1), (54, cy - 7 + 1)], fill=shade(YEL, 0.8))
    ty = cy - 12
    hw, h = 22, 28
    bx, by = 28, ty + 4
    sbox(d, bx, by, hw, h, (34, 56, 104, 255), NAVY_L, NAVY_R, (90, 120, 190, 255))
    for face, k in (('L', 1.0), ('R', 0.8)):
        fl, fd = new(hw - 1, 2)
        fd.rectangle([0, 0, hw - 2, 1], fill=shade(YEL, k))
        face_paste(img, fl, bx, by, hw, h, face, 1, 3)
        fl, fd = new(hw - 1, 10)
        col = shade(WHITE_C, k)
        for dx in (0, 1):
            pixel_text(fl, (0 + dx, -2), 'ZUS', 10, col)
        face_paste(img, fl, bx, by, hw, h, face, 1, 7)
        fl, fd = new(hw - 1, 5)
        fd.rectangle([2, 0, hw - 4, 4], fill=(8, 22, 54, 255))
        fd.point((hw - 6, 2), fill=YEL)
        fd.line([(4, 2), (9, 2)], fill=(90, 160, 230, 255))
        face_paste(img, fl, bx, by, hw, h, face, 1, 19)
    # dulang hitam + cawan putih berpita biru
    sbox(d, 28, ty + 13, 12, 3, (44, 44, 50, 255), (28, 28, 34, 255), (18, 18, 24, 255), (90, 90, 100, 255))
    d.rectangle([33, ty + 1, 37, ty + 7], fill=WHITE_C, outline=OL)
    d.rectangle([34, ty + 3, 36, ty + 5], fill=NAVY)
    d.line([(33, ty), (37, ty)], fill=(120, 80, 50, 255))
    return img


def machine_icecream():
    hs = 72
    img, d = new(56, hs)
    PINK, BLUE = (228, 0, 124, 255), (11, 58, 130, 255)
    cx, cy = box(d, hs, 6, (250, 250, 252, 255), BLUE, shade(BLUE, 0.72), WHITE_C)
    ty = cy - 6
    hw, h = 24, 24
    bx, by = 28, ty + 11
    sbox(d, bx, by, hw, h, (255, 236, 246, 255), PINK, shade(PINK, 0.72), (255, 170, 214, 255))
    tubs = [(228, 0, 124), (255, 255, 255), (96, 60, 38), (120, 200, 90), (250, 190, 40), (160, 100, 220)]
    for face, k in (('L', 1.0), ('R', 0.82)):
        # lencana BR putih
        fl, fd = new(hw - 1, 13)
        fd.rounded_rectangle([0, 0, hw - 2, 12], radius=2, fill=WHITE_C, outline=OL)
        bl, pk = shade(BLUE, k), shade(PINK, k)
        for dx in (0, 1):
            pixel_text(fl, (4 + dx, -1), 'B', 11, bl)
            pixel_text(fl, (13 + dx, -1), 'R', 11, pk)
        face_paste(img, fl, bx, by, hw, h, face, 1, 2)
        # tingkap kaca + tub 31 perisa
        fl, fd = new(hw - 1, 8)
        fd.rectangle([0, 0, hw - 2, 7], fill=(196, 226, 246, 255), outline=OL)
        for i in range(5):
            col = shade(tubs[(i + (0 if face == 'L' else 2)) % len(tubs)], k)
            fd.rectangle([2 + i * 4, 2, 4 + i * 4, 6], fill=col)
            fl.putpixel((2 + i * 4, 2), WHITE_C)
        face_paste(img, fl, bx, by, hw, h, face, 1, 15)
    # cone + 2 scoop (vanila, strawberi) di atas, cone menunjuk ke bawah
    ctop = by - h - hw // 2
    m = 28
    d.polygon([(m - 4, ctop - 7), (m + 4, ctop - 7), (m, ctop + 1)], fill=(222, 160, 84, 255), outline=OL)
    d.line([(m - 2, ctop - 6), (m + 1, ctop - 3)], fill=(176, 116, 56, 255))
    d.line([(m + 2, ctop - 6), (m - 1, ctop - 3)], fill=(176, 116, 56, 255))
    d.ellipse([m - 6, ctop - 15, m + 6, ctop - 5], fill=(255, 110, 168, 255), outline=OL)
    d.ellipse([m - 5, ctop - 22, m + 5, ctop - 13], fill=(255, 244, 214, 255), outline=OL)
    d.point((m - 3, ctop - 19), fill=WHITE_C)
    d.point((m - 3, ctop - 11), fill=(255, 190, 214, 255))
    d.rectangle([m, ctop - 24, m + 1, ctop - 23], fill=(228, 0, 60, 255))
    return img


def chiller_redbull():
    hs = 80
    img, d = new(56, hs)
    SIL_T, SIL_L, SIL_R = (226, 232, 240, 255), (196, 206, 218, 255), (150, 162, 180, 255)
    RB_RED, RB_BLUE, RB_YEL = (214, 24, 50, 255), (30, 66, 156, 255), (255, 204, 0, 255)
    hw, h = 28, 50
    bx, by = 28, hs
    HDR = 17
    sbox(d, bx, by, hw, h, SIL_T, SIL_L, SIL_R, WHITE_C)
    bull = ["......X.X.",
            "XXXXXXXXX.",
            "XXXXXXXXXX",
            "XXXXXXXXX.",
            "XXXXXXXXX.",
            "X.X...X.X.",
            "X.X...X.X."]

    mini = ["....X.X.",
            "XXXXXXX.",
            "XXXXXX..",
            "XXXXXX..",
            "X.X.X..."]

    def sun(fl, x0, y0, k, sz=6):
        fd = ImageDraw.Draw(fl)
        fd.ellipse([x0, y0, x0 + sz, y0 + sz], fill=shade(RB_YEL, k), outline=(200, 120, 0, 255))
        fl.putpixel((x0 + 2, y0 + 2), (255, 244, 170, 255))

    # papan tanda merah-kuning
    for face, k in (('L', 1.0), ('R', 0.82)):
        fl, fd = new(hw - 1, HDR)
        if face == 'L':
            fd.rectangle([0, 0, hw - 2, HDR - 1], fill=shade(RB_RED, k))
            pixel_text(fl, (0, -1), 'Red Bull', 7, (255, 255, 255, 255))
            sun(fl, 11, 9, k, 4)
            flat_rows(fl, 1, 9, mini, shade(RB_YEL, k))
            flat_rows(fl, hw - 1 - 8, 9, [r[::-1] for r in mini], shade(RB_YEL, k))
        else:
            fd.rectangle([0, 0, hw - 2, HDR - 1], fill=shade((238, 242, 248, 255), k))
            sun(fl, 10, 5, k)
            flat_rows(fl, 0, 5, bull, shade(RB_RED, k))
            flat_rows(fl, hw - 1 - 10, 5, [r[::-1] for r in bull], shade(RB_RED, k))
        fd.line([(0, 0), (hw - 2, 0)], fill=shade(RB_YEL, k))
        fd.line([(0, HDR - 1), (hw - 2, HDR - 1)], fill=shade(RB_YEL, k))
        fd.line([(0, HDR - 2), (hw - 2, HDR - 2)], fill=shade(RB_RED, k))
        face_paste(img, fl, bx, by, hw, h, face, 0, 0)
    # pintu kaca + 3 rak tin biru-perak
    gh = h - HDR - 4
    for face, k in (('L', 1.0), ('R', 0.82)):
        W = hw - 3
        fl, fd = new(W, gh)
        fd.rectangle([0, 0, W - 1, gh - 1], fill=(64, 70, 82, 255))
        gt, gb = (186, 232, 255), (116, 188, 240)
        for y in range(1, gh - 1):
            t = (y - 1) / max(1, gh - 3)
            col = tuple(int(gt[i] + (gb[i] - gt[i]) * t) for i in range(3))
            fd.line([(1, y), (W - 2, y)], fill=col + (255,))
        sh = (gh - 2) // 3
        for s in range(3):
            y0 = 1 + s * sh
            for i in range(5):
                x0 = 2 + i * 4
                blue = (i + s) % 2 == 0
                body = RB_BLUE if blue else (214, 220, 228, 255)
                fd.rectangle([x0, y0 + 1, x0 + 2, y0 + sh - 3], fill=body)
                fd.line([(x0, y0 + 1), (x0 + 2, y0 + 1)], fill=(250, 250, 252, 255))
                fd.point((x0 + 1, y0 + sh - 5), fill=RB_RED if blue else RB_BLUE)
            fd.line([(1, y0 + sh - 2), (W - 2, y0 + sh - 2)], fill=(120, 126, 140, 255))
        for i in range(3):  # kilau sejuk
            fl.putpixel((2 + i, 2 + i), WHITE_C)
        if k != 1.0:
            fl = shade_img(fl, k)
        face_paste(img, fl, bx, by, hw, h, face, 1, HDR)
    return img


# ---------------------------------------------------------------- bangunan 4 aras (sprite baharu)
# Pembantu isometrik: (u, v) = koordinat dalam tile (u sepanjang paksi c, v sepanjang paksi r, 0..1),
# z = tinggi piksel. Tile duduk di bahagian bawah kanvas: bucu atas (28, H-28), bucu bawah (28, H).

TEAK = dict(top=(184, 132, 86, 255), left=(152, 104, 64, 255), right=(122, 82, 50, 255), hi=(214, 170, 120, 255))
WALNUT = dict(top=(104, 64, 42, 255), left=(74, 44, 28, 255), right=(54, 32, 20, 255), hi=(156, 110, 78, 255))
STEEL = (178, 184, 196, 255)
STEEL_D = (110, 116, 130, 255)
GOLD = (214, 172, 72, 255)


def isop(H, u, v, z=0.0):
    return (int(math.floor(28 + (u - v) * 28 + 0.5)), int(math.floor(H - 28 + (u + v) * 14 - z + 0.5)))


def ibox(d, H, u0, u1, v0, v1, z0, z1, top, left, right, hi=None, ol=OL):
    """Peti isometrik selari paksi: muka kiri (v=v1), muka kanan (u=u1), atas (z1)."""
    p = lambda u, v, z: isop(H, u, v, z)
    d.polygon([p(u0, v1, z0), p(u1, v1, z0), p(u1, v1, z1), p(u0, v1, z1)], fill=left, outline=ol)
    d.polygon([p(u1, v1, z0), p(u1, v0, z0), p(u1, v0, z1), p(u1, v1, z1)], fill=right, outline=ol)
    d.polygon([p(u0, v0, z1), p(u1, v0, z1), p(u1, v1, z1), p(u0, v1, z1)], fill=top, outline=ol)
    if hi:
        a, b, c = p(u0, v1, z1), p(u0, v0, z1), p(u1, v0, z1)
        d.line([(a[0] + 2, a[1]), (b[0], b[1] + 1), (c[0] - 2, c[1])], fill=hi)


def paste_L(img, flat, x0, y0):
    """Tampal imej rata pada satah selari paksi c (muka kiri, turun ke kanan 1px / 2px)."""
    px = flat.load()
    for fx in range(flat.width):
        for fy in range(flat.height):
            c = px[fx, fy]
            x, y = x0 + fx, y0 + fy + fx // 2
            if c[3] and 0 <= x < img.width and 0 <= y < img.height:
                img.putpixel((x, y), c)


def paste_R(img, flat, x0, y0):
    """Tampal imej rata pada satah selari paksi r (muka kanan, naik ke kanan 1px / 2px)."""
    px = flat.load()
    for fx in range(flat.width):
        for fy in range(flat.height):
            c = px[fx, fy]
            x, y = x0 + fx, y0 + fy - (fx + 1) // 2
            if c[3] and 0 <= x < img.width and 0 <= y < img.height:
                img.putpixel((x, y), c)


def outline_alpha(img, color=OL):
    """Garis luar 1px di sekeliling piksel legap (untuk bentuk organik: daun, beanbag, payung)."""
    px = img.load()
    w, h = img.size
    solid = {(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0}
    for y in range(h):
        for x in range(w):
            if (x, y) not in solid and any((x + dx, y + dy) in solid for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = color
    return img


def legs4(d, H, pts, z, w=0.03, col=STEEL_D):
    """Kaki kecil di (u, v) yang diberi, dilukis belakang dulu."""
    for u, v in sorted(pts, key=lambda t: t[0] + t[1]):
        ibox(d, H, u - w, u + w, v - w, v + w, 0, z, col, shade(col, 0.85), shade(col, 0.7))


def laptop(d, H, u0, u1, v0, v1, z, body=(206, 210, 218, 255), screen=(110, 176, 238, 255)):
    """Laptop terbuka: tapak nipis + skrin menghadap +r (ke arah penonton kiri-bawah)."""
    p = lambda u, v, zz: isop(H, u, v, zz)
    ibox(d, H, u0, u1, v0, v1, z, z + 1, body, shade(body, 0.85), shade(body, 0.7))
    d.polygon([p(u0, v0, z + 1), p(u1, v0, z + 1), p(u1, v0, z + 10), p(u0, v0, z + 10)], fill=(46, 50, 62, 255), outline=OL)
    d.polygon([p(u0 + 0.04, v0, z + 3), p(u1 - 0.04, v0, z + 3), p(u1 - 0.04, v0, z + 8), p(u0 + 0.04, v0, z + 8)], fill=screen)
    a = p(u0 + 0.06, v0, z + 7)
    d.point((a[0] + 1, a[1]), fill=(230, 244, 255, 255))
    d.point((a[0] + 2, a[1] + 1), fill=(230, 244, 255, 255))
    d.line([p(u0 + 0.06, (v0 + v1) / 2, z + 1), p(u1 - 0.06, (v0 + v1) / 2, z + 1)], fill=shade(body, 0.75))


def stairs():
    """Tangga lurus naik ke belakang-kanan (arah -r): tapak maple, riser putih + jalur kuning,
    dinding sisi (stringer) putih dengan penutup biru, susur tangan di kedua-dua sisi."""
    H = 100
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    N, rh = 7, 8
    U0, U1 = 0.05, 0.82
    riser, rside = (250, 250, 252, 255), (204, 208, 216, 255)
    for k in range(N - 1, -1, -1):
        v0, v1 = 1 - (k + 1) / N, 1 - k / N
        z1 = (k + 1) * rh
        ibox(d, H, U0, U1, v0, v1, 0, z1, MAPLE['top'], riser, rside)
        a, b = p(U0, v1, z1), p(U1, v1, z1)
        d.line([(a[0] + 1, a[1] + 1), (b[0] - 1, b[1] + 1)], fill=G_YELLOW)  # jalur keselamatan
        c0, c1 = p(U0, v0, z1), p(U1, v0, z1)
        d.line([(c0[0] + 2, c0[1] + 1), (c1[0] - 1, c1[1] + 1)], fill=MAPLE['hi'])

    def znose(v):
        return min(N * rh, rh * (1 + (1 - v) * N))

    # susur tangan kiri (sisi belakang) di atas anak tangga
    ul = 0.07
    for v in (1 - 0.5 / N, 1 - 3.5 / N, 1 - 6.5 / N):
        k = int((1 - v) * N)
        a, b = p(ul, v, (k + 1) * rh), p(ul, v, znose(v) + 14)
        d.line([a, b], fill=STEEL_D)
    rail = [p(ul, 1, rh + 14), p(ul, 1 / N, N * rh + 14), p(ul, 0, N * rh + 14)]
    d.line(rail, fill=OL, width=3)
    d.line(rail, fill=(150, 98, 58, 255))
    # stringer kanan
    zt = lambda v: znose(v) + 4
    d.polygon([p(U1, 1, 0), p(1, 1, 0), p(1, 1, zt(1)), p(U1, 1, zt(1))], fill=(250, 250, 252, 255), outline=OL)
    d.polygon([p(1, 1, 0), p(1, 0, 0), p(1, 0, zt(0)), p(1, 1 / N, zt(1 / N)), p(1, 1, zt(1))], fill=(226, 230, 236, 255), outline=OL)
    d.polygon([p(1, 1, 1), p(1, 0, 1), p(1, 0, 5), p(1, 1, 5)], fill=G_BLUE)  # jalur biru tapak
    d.polygon([p(U1, 1, zt(1)), p(1, 1, zt(1)), p(1, 1 / N, zt(1 / N)), p(1, 0, zt(0)), p(U1, 0, zt(0)), p(U1, 1 / N, zt(1 / N))],
              fill=G_BLUE, outline=OL)
    # anak panah "naik" (chevron putih) pada dinding sisi
    for v in (0.72, 0.46):
        z = zt(v) - 14
        a, b, c = p(1, v + 0.1, z + 3), p(1, v, z + 6), p(1, v + 0.1, z + 9)
        d.line([a, b, c], fill=(255, 255, 255, 255), width=1)
        d.line([(a[0] + 1, a[1]), (b[0] + 1, b[1]), (c[0] + 1, c[1])], fill=(140, 184, 252, 255))
    # susur tangan kanan di atas stringer
    ur = 0.91
    for v in (0.9, 0.5, 0.12):
        d.line([p(ur, v, zt(v)), p(ur, v, zt(v) + 12)], fill=STEEL_D)
    rail = [p(ur, 1, zt(1) + 12), p(ur, 1 / N, zt(1 / N) + 12), p(ur, 0, zt(0) + 12)]
    d.line(rail, fill=OL, width=3)
    d.line(rail, fill=(170, 112, 66, 255))
    return img


def stair_hut():
    """Pondok tangga rooftop: dinding putih, bumbung rata, pintu biru menghadap +r, tanda EXIT hijau."""
    H = 94
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    d.polygon([p(0.3, 0.95, 0), p(0.7, 0.95, 0), p(0.7, 1.0, 0), p(0.3, 1.0, 0)], fill=(70, 74, 84, 255))  # alas kaki
    ibox(d, H, 0.06, 0.94, 0.06, 0.94, 0, 54, (230, 232, 236, 255), (246, 244, 238, 255), (212, 210, 202, 255))
    for face in ('L', 'R'):
        pts = [p(0.06, 0.94, 0), p(0.94, 0.94, 0), p(0.94, 0.94, 4), p(0.06, 0.94, 4)] if face == 'L' else \
              [p(0.94, 0.94, 0), p(0.94, 0.06, 0), p(0.94, 0.06, 4), p(0.94, 0.94, 4)]
        d.polygon(pts, fill=G_BLUE if face == 'L' else shade(G_BLUE, 0.78), outline=OL)
    ibox(d, H, 0.0, 1.0, 0.0, 1.0, 54, 60, (204, 208, 216, 255), (156, 162, 174, 255), (126, 132, 144, 255), (236, 240, 246, 255))
    # pintu
    d.polygon([p(0.3, 0.94, 0), p(0.7, 0.94, 0), p(0.7, 0.94, 38), p(0.3, 0.94, 38)], fill=(52, 104, 196, 255), outline=OL)
    d.polygon([p(0.37, 0.94, 22), p(0.63, 0.94, 22), p(0.63, 0.94, 34), p(0.37, 0.94, 34)], fill=(184, 222, 250, 255), outline=OL)
    a = p(0.4, 0.94, 31)
    d.point(a, fill=(255, 255, 255, 255))
    d.point((a[0] + 1, a[1] - 1), fill=(255, 255, 255, 255))
    h = p(0.62, 0.94, 17)
    d.rectangle([h[0] - 1, h[1], h[0], h[1] + 2], fill=GOLD)
    # tanda EXIT hijau di atas pintu
    d.polygon([p(0.36, 0.94, 43), p(0.64, 0.94, 43), p(0.64, 0.94, 49), p(0.36, 0.94, 49)], fill=G_GREEN, outline=OL)
    s = p(0.42, 0.94, 47)
    for i in range(5):
        d.point((s[0] + i, s[1] + i // 2), fill=(255, 255, 255, 255))
    # papan tanda tangga (biru, ikon anak tangga putih) pada muka kanan
    fl, fd = new(10, 10)
    fd.rectangle([0, 0, 9, 9], fill=shade(G_BLUE, 0.85), outline=OL)
    for k in range(4):
        fd.rectangle([2 + k * 2, 7 - k * 2, 3 + k * 2, 7], fill=(255, 255, 255, 255))
    x0, y0 = p(0.94, 0.62, 40)
    paste_R(img, fl, x0, y0)
    # lampu kecil di sisi pintu
    l = p(0.78, 0.94, 36)
    d.rectangle([l[0], l[1], l[0] + 1, l[1] + 2], fill=(255, 236, 160, 255), outline=OL)
    return img


def training_desk():
    """Meja latihan kecil putih berkaki keluli, laptop dan buku nota."""
    H = 56
    img, d = new(56, H)
    legs4(d, H, [(0.1, 0.22), (0.9, 0.22), (0.1, 0.78), (0.9, 0.78)], 12)
    ibox(d, H, 0.06, 0.94, 0.18, 0.82, 12, 15, WHITE['top'], WHITE['left'], WHITE['right'], WHITE['hi'])
    laptop(d, H, 0.3, 0.62, 0.36, 0.6, 15)
    p = lambda u, v, z: isop(H, u, v, z)
    d.polygon([p(0.66, 0.5, 15), p(0.86, 0.5, 15), p(0.86, 0.74, 15), p(0.66, 0.74, 15)], fill=(250, 246, 230, 255), outline=OL)
    d.line([p(0.7, 0.6, 15), p(0.82, 0.6, 15)], fill=G_BLUE)
    d.line([p(0.7, 0.66, 15), p(0.8, 0.66, 15)], fill=(170, 176, 190, 255))
    return img


def chart_flat(w, h):
    """Kandungan carta ringkas (bar warna Google + garis trend) untuk skrin projektor."""
    fl, fd = new(w, h)
    fd.rectangle([0, 0, w - 1, h - 1], fill=(252, 252, 252, 255), outline=(150, 156, 168, 255))
    fd.line([(3, 3), (14, 3)], fill=(60, 64, 76, 255))
    fd.line([(3, 5), (10, 5)], fill=(170, 176, 188, 255))
    fd.line([(4, 8), (4, h - 4), (w - 4, h - 4)], fill=(110, 116, 128, 255))
    bars = [(G_BLUE, 5), (G_RED, 8), (G_YELLOW, 7), (G_GREEN, 11), (G_BLUE, 14)]
    for i, (col, bh) in enumerate(bars):
        x = 7 + i * 5
        fd.rectangle([x, h - 5 - bh, x + 2, h - 5], fill=col)
    pts = [(8, h - 10), (13, h - 13), (18, h - 12), (23, h - 17), (28, h - 21)]
    fd.line(pts, fill=(52, 120, 80, 255))
    fd.ellipse([w - 9, 3, w - 4, 8], fill=G_YELLOW, outline=(180, 130, 0, 255))
    fd.pieslice([w - 9, 3, w - 4, 8], -90, 30, fill=G_BLUE)
    return fl


def projector_screen():
    """Skrin projektor tarik-naik atas tripod; satah skrin selari paksi c (menghadap +r)."""
    H = 86
    img, d = new(56, H)
    hub = (28, H - 32)
    d.line([hub, (30, H - 19)], fill=(70, 74, 84, 255), width=2)  # kaki belakang
    d.rectangle([27, H - 74, 28, hub[1]], fill=(80, 84, 94, 255))  # tiang
    W, Hs = 37, 32
    fl, fd = new(W, Hs)
    fd.rounded_rectangle([0, 0, W - 1, 3], radius=1, fill=(64, 68, 80, 255), outline=OL)
    fd.rectangle([1, 4, W - 2, Hs - 1], fill=(210, 214, 222, 255), outline=OL)
    fl.alpha_composite(chart_flat(W - 4, Hs - 7), (2, 5))
    fd.line([(W // 2 - 1, Hs - 1), (W // 2 + 1, Hs - 1)], fill=(64, 68, 80, 255))
    x0, y0 = isop(H, -0.15, 0.5, 60)
    paste_L(img, fl, x0, y0)
    d.line([hub, (17, H - 12)], fill=(80, 84, 94, 255), width=2)  # kaki depan
    d.line([hub, (40, H - 12)], fill=(80, 84, 94, 255), width=2)
    for x, y in ((17, H - 12), (40, H - 12), (30, H - 19)):
        d.rectangle([x - 1, y, x + 1, y + 1], fill=OL)
    d.rectangle([26, hub[1] - 1, 29, hub[1] + 1], fill=(50, 54, 62, 255), outline=OL)
    return img


def whiteboard():
    """Whiteboard bergerak (tiang + roda) dengan contengan warna; satah selari paksi c."""
    H = 76
    img, d = new(56, H)
    W, Hb = 40, 27
    x0, y0 = isop(H, -0.2, 0.5, 50)
    # tiang kiri & kanan (lukis dulu, papan menindih)
    lp, rp = (x0 - 1, y0 - 2), (x0 + W, y0 + W // 2 - 2)
    lg, rg = (lp[0], isop(H, -0.22, 0.5, 0)[1]), (rp[0], rp[1] + 50)
    for top, bot in ((lp, lg), (rp, rg)):
        d.rectangle([top[0] - 1, top[1], top[0] + 1, bot[1]], fill=STEEL, outline=OL)
    fl, fd = new(W, Hb)
    fd.rectangle([0, 0, W - 1, Hb - 1], fill=(196, 202, 212, 255), outline=OL)
    fd.rectangle([2, 2, W - 3, Hb - 6], fill=(253, 253, 253, 255))
    fd.rectangle([1, Hb - 4, W - 2, Hb - 2], fill=(150, 158, 170, 255), outline=OL)
    for i, col in enumerate((G_RED, G_BLUE, G_GREEN)):
        fd.line([(6 + i * 4, Hb - 3), (8 + i * 4, Hb - 3)], fill=col)
    fd.line([(4, 5), (7, 4), (10, 5), (13, 4), (16, 5)], fill=G_BLUE)       # tajuk
    fd.rectangle([4, 9, 12, 15], outline=G_RED)                             # kotak
    fd.line([(13, 12), (19, 12)], fill=(60, 64, 76, 255))                   # anak panah
    fd.line([(17, 10), (19, 12), (17, 14)], fill=(60, 64, 76, 255))
    fd.ellipse([20, 8, 29, 16], outline=G_GREEN)
    fd.line([(23, 12), (24, 14), (27, 10)], fill=G_GREEN)                   # tanda betul
    fd.rectangle([31, 4, 36, 9], fill=(253, 230, 138, 255), outline=(200, 160, 40, 255))  # nota lekat
    for y in (18, 20):
        fd.line([(4, y), (4 + (24 if y == 18 else 16), y)], fill=(150, 156, 170, 255))
    paste_L(img, fl, x0, y0)
    # kaki T + roda
    for g in (lg, rg):
        d.line([(g[0] - 4, g[1] + 2), (g[0] + 4, g[1] - 2)], fill=OL, width=2)
        for wx, wy in ((g[0] - 4, g[1] + 2), (g[0] + 4, g[1] - 2)):
            d.rectangle([wx - 1, wy, wx, wy + 1], fill=(40, 40, 46, 255))
    return img


def coffee_table():
    """Meja kopi rendah kayu dengan majalah dan cawan."""
    H = 40
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    wood = dict(top=(160, 108, 66, 255), left=(128, 84, 50, 255), right=(100, 64, 38, 255), hi=(196, 146, 100, 255))
    legs4(d, H, [(0.16, 0.16), (0.84, 0.16), (0.16, 0.84), (0.84, 0.84)], 8, 0.035, (90, 58, 34, 255))
    ibox(d, H, 0.1, 0.9, 0.1, 0.9, 8, 11, wood['top'], wood['left'], wood['right'], wood['hi'])
    z = 11
    d.polygon([p(0.22, 0.42, z), p(0.52, 0.42, z), p(0.52, 0.7, z), p(0.22, 0.7, z)], fill=G_BLUE, outline=OL)
    d.line([p(0.27, 0.5, z), p(0.46, 0.5, z)], fill=(255, 255, 255, 255))
    d.polygon([p(0.3, 0.52, z + 1), p(0.58, 0.6, z + 1), p(0.5, 0.86, z + 1), p(0.22, 0.78, z + 1)], fill=(250, 246, 236, 255), outline=OL)
    d.line([p(0.32, 0.62, z + 1), p(0.5, 0.68, z + 1)], fill=G_RED)
    for (u, v) in ((0.7, 0.32), (0.66, 0.62)):
        x, y = p(u, v, z)
        d.rectangle([x - 2, y - 4, x + 1, y], fill=(255, 255, 255, 255), outline=OL)
        d.line([(x - 1, y - 4), (x, y - 4)], fill=(110, 66, 36, 255))
    return img


def exec_desk():
    """Meja eksekutif walnut gelap: trim emas, monitor, lampu banker hijau, plat nama."""
    H = 70
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    box(d, H, 18, WALNUT['top'], WALNUT['left'], WALNUT['right'], WALNUT['hi'])
    d.line([p(0.03, 1, 14), p(0.97, 1, 14)], fill=GOLD)
    d.line([p(1, 0.97, 14), p(1, 0.03, 14)], fill=shade(GOLD, 0.75))
    d.polygon([p(0.14, 1, 3), p(0.86, 1, 3), p(0.86, 1, 11), p(0.14, 1, 11)], outline=(52, 30, 18, 255))
    d.polygon([p(1, 0.86, 3), p(1, 0.14, 3), p(1, 0.14, 11), p(1, 0.86, 11)], outline=(38, 22, 13, 255))
    t = p(0.5, 0.5, 18)  # pusat muka atas
    d.line([(t[0] - 18, t[1]), (t[0] - 4, t[1] - 7)], fill=(128, 84, 58, 255))  # kilau
    # monitor nipis
    d.rectangle([t[0] - 6, t[1] - 22, t[0] + 9, t[1] - 11], fill=(30, 32, 40, 255), outline=OL)
    d.rectangle([t[0] - 4, t[1] - 20, t[0] + 7, t[1] - 13], fill=(36, 72, 132, 255))
    d.line([(t[0] - 3, t[1] - 19), (t[0] + 1, t[1] - 19)], fill=(140, 190, 250, 255))
    d.rectangle([t[0] + 1, t[1] - 10, t[0] + 2, t[1] - 7], fill=(60, 62, 70, 255))
    d.rectangle([t[0] - 2, t[1] - 7, t[0] + 5, t[1] - 6], fill=(60, 62, 70, 255), outline=OL)
    # lampu banker: tapak tembaga + tudung hijau
    lx, ly = t[0] - 15, t[1] - 3
    d.rectangle([lx - 2, ly - 1, lx + 2, ly], fill=GOLD, outline=OL)
    d.line([(lx, ly - 2), (lx, ly - 8)], fill=GOLD)
    d.polygon([(lx - 5, ly - 8), (lx + 5, ly - 8), (lx + 3, ly - 12), (lx - 3, ly - 12)], fill=(24, 120, 60, 255), outline=OL)
    d.line([(lx - 2, ly - 11), (lx + 2, ly - 11)], fill=(90, 190, 120, 255))
    d.line([(lx - 3, ly - 7), (lx + 3, ly - 7)], fill=(255, 236, 160, 255))
    # kertas + pen
    d.polygon([(t[0] + 10, t[1] + 1), (t[0] + 17, t[1] - 2), (t[0] + 21, t[1]), (t[0] + 14, t[1] + 3)], fill=(246, 244, 236, 255), outline=OL)
    d.line([(t[0] + 13, t[1] + 4), (t[0] + 19, t[1] + 1)], fill=GOLD)
    # plat nama emas di depan
    n = p(0.5, 0.82, 18)
    d.polygon([(n[0] - 7, n[1] - 1), (n[0] + 1, n[1] + 3), (n[0] + 1, n[1] + 1), (n[0] - 7, n[1] - 3)], fill=(40, 30, 24, 255), outline=OL)
    d.line([(n[0] - 6, n[1] - 2), (n[0], n[1] + 1)], fill=GOLD)
    return img


def glass_wall():
    """Dinding kaca pejabat: geometri sama partition (garisan a->b melalui tengah tile) tetapi
    lebih tinggi. Kanvas 56x96, tengah tile (28, 82). Kaca separa lut sinar (RGBA) + jalur frosted."""
    img, d = new(56, 96)
    a, b = (14, 75), (42, 89)
    h = 62
    frame, frame_l = (150, 160, 174, 255), (214, 220, 230, 255)
    seg = lambda z0, z1: [(a[0], a[1] - z0), (b[0], b[1] - z0), (b[0], b[1] - z1), (a[0], a[1] - z1)]
    d.polygon(seg(4, h - 3), fill=(178, 216, 244, 88))
    d.polygon(seg(26, 35), fill=(234, 244, 252, 196))
    d.line([(a[0], a[1] - 26), (b[0], b[1] - 26)], fill=(206, 222, 236, 220))
    for k, (dx0, dz0, dx1, dz1) in enumerate(((4, 10, 10, 24), (6, 40, 12, 56), (16, 42, 20, 52))):
        d.line([(a[0] + dx0, a[1] + dx0 // 2 - dz0), (a[0] + dx1, a[1] + dx1 // 2 - dz1)], fill=(255, 255, 255, 150 if k < 2 else 110))
    d.polygon(seg(0, 4), fill=frame, outline=OL)                                        # rel bawah
    d.polygon(seg(h - 3, h), fill=frame_l, outline=OL)                                  # rel atas
    d.polygon([(a[0], a[1] - h), (b[0], b[1] - h), (b[0] + 2, b[1] - h - 1), (a[0] + 2, a[1] - h - 1)],
              fill=(236, 240, 246, 255), outline=OL)
    d.line([(a[0], a[1]), (a[0], a[1] - h)], fill=OL)                                   # tiang hujung
    d.line([(a[0] + 1, a[1] - 1), (a[0] + 1, a[1] - h + 1)], fill=frame)
    d.polygon([b, (b[0], b[1] - h), (b[0] + 2, b[1] - h - 1), (b[0] + 2, b[1] - 1)], fill=frame, outline=OL)
    return img


def railing():
    """Pagar kaca tepi bangunan pada tepi hadapan-kiri tile (+r), sepanjang paksi c."""
    H = 56
    img, d = new(56, H)
    a, b = (0, H - 14), (28, H)
    rh = 22
    seg = lambda z0, z1: [(a[0], a[1] - z0), (b[0], b[1] - z0), (b[0], b[1] - z1), (a[0], a[1] - z1)]
    d.polygon(seg(3, rh - 2), fill=(188, 224, 250, 96))
    d.line([(a[0] + 5, a[1] + 2 - 6), (a[0] + 9, a[1] + 4 - 16)], fill=(255, 255, 255, 150))
    d.line([(a[0] + 15, a[1] + 7 - 5), (a[0] + 18, a[1] + 9 - 12)], fill=(255, 255, 255, 110))
    d.polygon(seg(0, 3), fill=(118, 124, 136, 255), outline=OL)
    d.polygon(seg(rh - 2, rh + 1), fill=(210, 216, 226, 255), outline=OL)
    d.line([(a[0] + 1, a[1] - rh), (b[0] - 1, b[1] - rh)], fill=(255, 255, 255, 255))
    for x, y in (a, b):
        d.line([(x, y - 1), (x, y - rh)], fill=STEEL_D)
    return img


def arcade():
    """Kabinet arked: marquee bercahaya, skrin game, panel kawalan, seni sisi warna Google."""
    H = 78
    img, d = new(56, H)
    bx, by, hw, h = 28, H - 7, 14, 50
    body_l, body_r = (56, 50, 112, 255), (38, 34, 80, 255)
    sbox(d, bx, by, hw, h, (30, 30, 42, 255), body_l, body_r, (96, 90, 160, 255))
    W = hw - 2
    mq, md = new(W, 6)
    md.rectangle([0, 0, W - 1, 5], fill=G_YELLOW, outline=OL)
    for i, col in enumerate((G_RED, G_BLUE, G_GREEN, G_RED)):
        md.rectangle([1 + i * 3, 2, 2 + i * 3, 3], fill=col)
    face_paste(img, mq, bx, by, hw, h, 'L', 1, 2)
    sc, sd = new(W, 13)
    sd.rectangle([0, 0, W - 1, 12], fill=(10, 14, 34, 255), outline=(90, 210, 255, 255))
    inv = ["..X.X..", ".XXXXX.", "XX.X.XX", "XXXXXXX", ".X...X."]
    for gy, row in enumerate(inv):
        for gx, ch in enumerate(row):
            if ch == 'X':
                sc.putpixel((2 + gx, 2 + gy), (110, 240, 120, 255))
    for x, y, col in ((9, 3, G_YELLOW), (3, 9, G_RED), (6, 10, G_BLUE), (9, 9, (255, 255, 255, 255))):
        sc.putpixel((x, y), col)
    face_paste(img, sc, bx, by, hw, h, 'L', 1, 9)
    cp, cd = new(W, 7)
    cd.rectangle([0, 0, W - 1, 6], fill=(40, 40, 50, 255), outline=OL)
    cd.rectangle([2, 1, 3, 2], fill=G_RED)
    cd.line([(2, 3), (2, 4)], fill=(20, 20, 24, 255))
    for i, col in enumerate((G_BLUE, G_YELLOW, G_GREEN)):
        cp.putpixel((6 + i * 2, 3 + (i % 2)), col)
    face_paste(img, cp, bx, by, hw, h, 'L', 1, 24)
    cn, ccd = new(5, 6)
    ccd.rectangle([0, 0, 4, 5], fill=(26, 26, 34, 255), outline=OL)
    ccd.line([(2, 1), (2, 3)], fill=(255, 150, 40, 255))
    face_paste(img, cn, bx, by, hw, h, 'L', 4, 36)
    side, sdd = new(hw - 1, 44)
    for i, col in enumerate((G_BLUE, G_RED, G_YELLOW, G_GREEN)):
        y = 6 + i * 9
        sdd.polygon([(0, y + 6), (hw - 2, y), (hw - 2, y + 4), (0, y + 10)], fill=shade(col, 0.75))
    face_paste(img, side, bx, by, hw, h, 'R', 0, 3)
    return img


def tv_console():
    """TV besar atas kabinet rendah, konsol game putih + controller. Skrin menghadap +r."""
    H = 70
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    cab = dict(top=(112, 80, 56, 255), left=(90, 62, 42, 255), right=(70, 48, 32, 255), hi=(150, 112, 80, 255))
    ibox(d, H, 0.04, 0.96, 0.36, 0.92, 0, 12, cab['top'], cab['left'], cab['right'], cab['hi'])
    d.line([p(0.5, 0.92, 2), p(0.5, 0.92, 10)], fill=OL)
    for u in (0.44, 0.56):
        d.line([p(u, 0.92, 5), p(u, 0.92, 7)], fill=STEEL)
    ibox(d, H, 0.42, 0.58, 0.48, 0.58, 12, 15, (40, 40, 46, 255), (30, 30, 36, 255), (22, 22, 28, 255))
    ibox(d, H, 0.0, 1.0, 0.48, 0.55, 15, 46, (44, 44, 52, 255), (22, 22, 28, 255), (16, 16, 20, 255))
    W, Hs = 26, 28
    fl, fd = new(W, Hs)
    for y in range(Hs):
        t = y / (Hs - 1)
        fd.line([(0, y), (W - 1, y)], fill=(int(96 + 70 * t), int(170 + 50 * t), 250, 255))
    fd.rectangle([0, Hs - 7, W - 1, Hs - 1], fill=(70, 170, 70, 255))
    fd.rectangle([0, Hs - 4, W - 1, Hs - 1], fill=(150, 100, 54, 255))
    for x in range(0, W, 4):
        fd.point((x, Hs - 4), fill=(190, 140, 80, 255))
    fd.ellipse([3, 4, 10, 8], fill=(255, 255, 255, 255))
    fd.ellipse([15, 2, 21, 6], fill=(255, 255, 255, 255))
    fd.rectangle([6, Hs - 13, 9, Hs - 8], fill=G_RED)        # hero merah
    fd.rectangle([6, Hs - 14, 9, Hs - 13], fill=(140, 40, 30, 255))
    fd.rectangle([17, Hs - 11, 20, Hs - 8], fill=G_BLUE)     # musuh biru
    fd.rectangle([12, Hs - 17, 13, Hs - 16], fill=G_YELLOW)  # syiling
    fd.rectangle([14, Hs - 20, 22, Hs - 18], fill=(196, 120, 60, 255))
    x0, y0 = p(0.04, 0.55, 43)
    paste_L(img, fl, x0, y0)
    ibox(d, H, 0.08, 0.34, 0.72, 0.9, 12, 15, (246, 246, 250, 255), (224, 226, 232, 255), (190, 194, 204, 255))
    d.line([p(0.12, 0.9, 13), p(0.3, 0.9, 13)], fill=G_BLUE)
    c = p(0.72, 0.78, 12)
    d.ellipse([c[0] - 4, c[1] - 2, c[0] + 3, c[1] + 1], fill=(44, 44, 52, 255), outline=OL)
    d.point((c[0] + 1, c[1] - 1), fill=G_RED)
    d.point((c[0] - 2, c[1] - 1), fill=G_BLUE)
    return img


def beanbag(color):
    H = 40
    img = Image.new('RGBA', (56, H), (0, 0, 0, 0))
    lay, d = new(56, H)
    d.ellipse([9, H - 27, 47, H - 6], fill=shade(color, 0.62))
    d.ellipse([10, H - 30, 45, H - 9], fill=shade(color, 0.82))
    d.ellipse([22, H - 38, 45, H - 18], fill=shade(color, 0.95))  # sandaran
    d.ellipse([25, H - 37, 37, H - 30], fill=shade(color, 1.18))
    d.ellipse([12, H - 26, 34, H - 13], fill=shade(color, 1.05))  # lekuk tempat duduk
    d.ellipse([15, H - 24, 26, H - 19], fill=shade(color, 1.22))
    d.line([(24, H - 15), (32, H - 20)], fill=shade(color, 0.7))
    d.line([(40, H - 12), (44, H - 16)], fill=shade(color, 0.5))
    outline_alpha(lay)
    img.alpha_composite(lay)
    return img


def umbrella_table():
    """Meja patio bulat + payung jalur warna Google."""
    H = 98
    img, d = new(56, H)
    yt = H - 14 - 16
    d.ellipse([22, H - 18, 34, H - 11], fill=(110, 116, 128, 255), outline=OL)
    d.rectangle([26, yt, 29, H - 14], fill=(170, 176, 188, 255), outline=OL)
    d.ellipse([12, yt - 6, 44, yt + 9], fill=(196, 200, 208, 255), outline=OL)
    d.ellipse([12, yt - 8, 44, yt + 6], fill=(248, 248, 248, 255), outline=OL)
    d.arc([15, yt - 6, 41, yt + 4], 200, 300, fill=(255, 255, 255, 255))
    A = H - 14 - 78
    R = H - 14 - 62
    d.rectangle([26, A, 29, yt - 2], fill=(226, 228, 232, 255), outline=OL)  # tiang
    can, cd = new(56, H)
    rx, ry = 27, 9
    rim = [(28 + rx * math.cos(math.radians(22.5 + i * 45)), R + ry * math.sin(math.radians(22.5 + i * 45))) for i in range(8)]
    cols = [G_BLUE, G_RED, G_YELLOW, G_GREEN]
    order = sorted(range(8), key=lambda i: rim[i][1] + rim[(i + 1) % 8][1])
    for i in order:
        r0, r1 = rim[i], rim[(i + 1) % 8]
        mid = math.radians(22.5 + (i + 0.5) * 45)
        f = 1.0 - 0.14 * math.cos(mid)
        cd.polygon([(28, A), r0, r1], fill=shade(cols[i % 4], f))
        if (r0[1] + r1[1]) / 2 > R - 2:  # valance berkelok di hadapan
            m = ((r0[0] + r1[0]) / 2, (r0[1] + r1[1]) / 2 + 3)
            cd.polygon([r0, r1, m], fill=shade(cols[i % 4], f * 0.82))
    for i in range(8):
        if rim[i][1] > R - 4:
            cd.line([(28, A), rim[i]], fill=(255, 255, 255, 120))
    outline_alpha(can)
    img.alpha_composite(can)
    d.rectangle([27, A - 3, 28, A], fill=(240, 240, 244, 255), outline=OL)  # finial
    return img


def lounger():
    """Kerusi rehat kayu (sepanjang paksi c), sandaran di hujung belakang, kusyen jalur biru/putih."""
    H = 50
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    legs4(d, H, [(0.08, 0.34), (0.92, 0.34), (0.08, 0.68), (0.92, 0.68)], 6, 0.025, TEAK['right'])
    ibox(d, H, 0.03, 0.97, 0.3, 0.72, 5, 8, TEAK['top'], TEAK['left'], TEAK['right'], TEAK['hi'])
    # sandaran condong
    d.polygon([p(0.06, 0.72, 8), p(0.3, 0.72, 8), p(0.08, 0.72, 26)], fill=TEAK['left'], outline=OL)
    d.polygon([p(0.3, 0.3, 8), p(0.3, 0.72, 8), p(0.08, 0.72, 26), p(0.08, 0.3, 26)], fill=TEAK['top'], outline=OL)
    d.polygon([p(0.28, 0.34, 10), p(0.28, 0.68, 10), p(0.11, 0.68, 24), p(0.11, 0.34, 24)], fill=(250, 250, 250, 255), outline=OL)
    for k in range(3):  # jalur biru pada kusyen sandaran
        z = 13 + k * 4
        u = 0.28 - (z - 10) / 14 * 0.17
        d.line([p(u, 0.36, z), p(u, 0.66, z)], fill=G_BLUE)
    # kusyen tempat duduk
    ibox(d, H, 0.32, 0.95, 0.34, 0.68, 8, 11, (250, 250, 250, 255), (226, 230, 236, 255), (196, 202, 212, 255))
    for u in (0.4, 0.54, 0.68, 0.82):
        d.line([p(u, 0.36, 11), p(u, 0.67, 11)], fill=G_BLUE)
        d.line([p(u, 0.68, 10), p(u, 0.68, 9)], fill=shade(G_BLUE, 0.8))
    t = p(0.62, 0.42, 11)  # tuala kuning dilipat
    d.polygon([(t[0] - 4, t[1]), (t[0], t[1] - 2), (t[0] + 4, t[1]), (t[0], t[1] + 2)], fill=G_YELLOW, outline=OL)
    return img


def bbq():
    """Gril BBQ kettle: tudung merah tertutup, mangkuk hitam, 3 kaki, roda."""
    H = 66
    img = Image.new('RGBA', (56, H), (0, 0, 0, 0))
    lay, d = new(56, H)
    Yc = H - 14 - 28
    leg = (86, 90, 100, 255)
    d.line([(28, Yc + 6), (30, H - 18)], fill=shade(leg, 0.7), width=2)
    d.polygon([(21, H - 23), (35, H - 23), (30, H - 20), (24, H - 20)], fill=(150, 156, 168, 255))
    d.line([(20, Yc + 6), (16, H - 13)], fill=leg, width=2)
    d.line([(36, Yc + 6), (40, H - 13)], fill=leg, width=2)
    d.ellipse([14, H - 16, 18, H - 12], fill=(30, 30, 34, 255))
    d.ellipse([38, H - 16, 42, H - 12], fill=(30, 30, 34, 255))
    d.chord([14, Yc - 10, 42, Yc + 10], 0, 180, fill=(44, 44, 50, 255))
    d.chord([14, Yc - 15, 42, Yc + 15], 180, 360, fill=(206, 54, 42, 255))
    d.chord([17, Yc - 13, 34, Yc + 5], 190, 280, fill=(240, 104, 86, 255))
    d.line([(15, Yc), (41, Yc)], fill=(130, 30, 24, 255))
    d.line([(15, Yc + 1), (41, Yc + 1)], fill=(150, 156, 168, 255))
    d.rectangle([12, Yc - 1, 14, Yc + 1], fill=(30, 30, 34, 255))
    d.rectangle([42, Yc - 1, 44, Yc + 1], fill=(30, 30, 34, 255))
    d.rectangle([25, Yc - 18, 31, Yc - 17], fill=(200, 206, 214, 255))  # pemegang
    d.point((25, Yc - 16), fill=(200, 206, 214, 255))
    d.point((31, Yc - 16), fill=(200, 206, 214, 255))
    for x in (21, 23):
        d.point((x, Yc - 9), fill=(120, 26, 20, 255))
    d.rectangle([33, Yc - 7, 35, Yc - 5], fill=(240, 240, 240, 255))  # termometer
    d.point((34, Yc - 6), fill=OL)
    d.rectangle([24, Yc + 4, 32, Yc + 6], fill=(28, 28, 32, 255))
    outline_alpha(lay)
    img.alpha_composite(lay)
    return img


def planter():
    """Kotak penanam kayu berjalur dengan pokok renek dan bunga warna Google."""
    H = 58
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ibox(d, H, 0.06, 0.94, 0.06, 0.94, 0, 14, TEAK['top'], TEAK['left'], TEAK['right'], TEAK['hi'])
    for z in (5, 10):
        d.line([p(0.07, 0.94, z), p(0.93, 0.94, z)], fill=shade(TEAK['left'], 0.78))
        d.line([p(0.94, 0.93, z), p(0.94, 0.07, z)], fill=shade(TEAK['right'], 0.78))
    d.polygon([p(0.14, 0.14, 14), p(0.86, 0.14, 14), p(0.86, 0.86, 14), p(0.14, 0.86, 14)], fill=(88, 60, 40, 255), outline=OL)
    fol, fd = new(56, H)
    cy = H - 28 - 6
    dark, mid, light = (44, 98, 50, 255), (70, 138, 66, 255), (112, 176, 92, 255)
    for (x, y, r) in ((16, cy - 2, 8), (40, cy - 2, 8), (24, cy - 9, 9), (34, cy - 10, 9), (28, cy + 1, 9), (29, cy - 17, 6)):
        fd.ellipse([x - r, y - r, x + r, y + r], fill=mid)
    rnd = random.Random(21)
    for _ in range(70):
        x, y = rnd.randint(6, 50), rnd.randint(cy - 24, cy + 10)
        if fol.getpixel((x, y))[3]:
            fd.rectangle([x, y, x + 1, y], fill=light if rnd.random() < 0.5 else dark)
    for (x, y), col in zip(((14, cy - 4), (22, cy - 12), (33, cy - 6), (38, cy - 13), (27, cy - 18), (42, cy - 2), (20, cy + 1), (30, cy - 1)),
                           (G_RED, G_YELLOW, (255, 255, 255, 255), G_RED, G_YELLOW, G_BLUE, (255, 255, 255, 255), G_RED)):
        fd.rectangle([x, y, x + 1, y + 1], fill=col)
    outline_alpha(fol, (30, 64, 36, 255))
    img.alpha_composite(fol)
    return img


def outdoor_desk():
    """Meja kerja luar: permukaan jati berjalur, kaki logam hitam, laptop dan cawan."""
    H = 58
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    blk = (40, 42, 48, 255)
    for u in (0.12, 0.88):
        d.line([p(u, 0.18, 13), p(u, 0.24, 0)], fill=blk, width=2)
        d.line([p(u, 0.82, 13), p(u, 0.76, 0)], fill=blk, width=2)
        d.line([p(u, 0.21, 5), p(u, 0.79, 5)], fill=blk)
    ibox(d, H, 0.04, 0.96, 0.12, 0.88, 13, 16, TEAK['top'], TEAK['left'], TEAK['right'], TEAK['hi'])
    for v in (0.31, 0.5, 0.69):
        d.line([p(0.06, v, 16), p(0.94, v, 16)], fill=shade(TEAK['top'], 0.82))
    laptop(d, H, 0.3, 0.62, 0.34, 0.58, 16, body=(196, 200, 208, 255))
    x, y = p(0.78, 0.6, 16)
    d.rectangle([x - 2, y - 4, x + 1, y], fill=(255, 255, 255, 255), outline=OL)
    d.line([(x - 1, y - 4), (x, y - 4)], fill=(110, 66, 36, 255))
    return img


def ac_unit():
    """Unit kondenser aircond rooftop: kotak kelabu, kipas bulat pada muka hadapan, sirip di sisi."""
    H = 56
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ibox(d, H, 0.04, 0.96, 0.1, 0.9, 0, 3, (168, 170, 172, 255), (140, 142, 146, 255), (118, 120, 124, 255))
    ibox(d, H, 0.08, 0.92, 0.18, 0.82, 3, 28, (226, 230, 236, 255), (206, 212, 220, 255), (162, 170, 182, 255), (246, 248, 252, 255))
    fl, fd = new(22, 22)
    fd.ellipse([1, 1, 20, 20], fill=(70, 76, 88, 255), outline=OL)
    fd.ellipse([4, 4, 17, 17], outline=(120, 128, 142, 255))
    for ang in (20, 110, 200, 290):
        a = math.radians(ang)
        fd.line([(10.5, 10.5), (10.5 + 7 * math.cos(a), 10.5 + 7 * math.sin(a))], fill=(150, 158, 172, 255), width=2)
    fd.ellipse([8, 8, 13, 13], fill=(196, 202, 212, 255), outline=OL)
    x0, y0 = p(0.14, 0.82, 26)
    paste_L(img, fl, x0, y0)
    for i in range(1, 11):  # sirip
        v = 0.8 - i * 0.056
        d.line([p(0.92, v, 6), p(0.92, v, 25)], fill=(140, 148, 160, 255))
    for i in range(1, 6):  # gril atas
        u = 0.08 + i * 0.14
        d.line([p(u, 0.22, 28), p(u, 0.78, 28)], fill=(190, 196, 206, 255))
    d.rectangle([p(0.66, 0.82, 24)[0], p(0.66, 0.82, 24)[1], p(0.66, 0.82, 24)[0] + 3, p(0.66, 0.82, 24)[1] + 1], fill=G_BLUE)
    pa, pb = p(0.92, 0.3, 10), p(0.92, 0.3, 4)
    d.line([pa, (pa[0] + 5, pa[1] - 2), (pa[0] + 5, pa[1] + 8)], fill=(196, 120, 60, 255), width=2)  # paip tembaga
    return img


def pantry_counter():
    """Kaunter dapur: kabinet putih (pemegang biru), permukaan batu kelabu, sinki keluli + pili, rak pinggan."""
    H = 60
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    box(d, H, 20, (214, 216, 222, 255), (246, 246, 248, 255), (208, 212, 218, 255), (240, 242, 246, 255))
    d.polygon([p(0, 1, 0), p(1, 1, 0), p(1, 1, 3), p(0, 1, 3)], fill=(84, 90, 102, 255), outline=OL)
    d.polygon([p(1, 1, 0), p(1, 0, 0), p(1, 0, 3), p(1, 1, 3)], fill=(66, 72, 84, 255), outline=OL)
    d.line([p(0, 1, 17), p(1, 1, 17)], fill=(170, 174, 182, 255))
    d.line([p(1, 1, 17), p(1, 0, 17)], fill=(150, 154, 162, 255))
    d.line([p(0.5, 1, 4), p(0.5, 1, 16)], fill=(180, 184, 192, 255))
    d.line([p(1, 0.5, 4), p(1, 0.5, 16)], fill=(160, 164, 172, 255))
    for u in (0.42, 0.58):
        a = p(u, 1, 13)
        d.line([a, (a[0], a[1] + 3)], fill=G_BLUE)
    for v in (0.42, 0.58):
        a = p(1, v, 13)
        d.line([a, (a[0], a[1] + 3)], fill=shade(G_BLUE, 0.8))
    z = 20
    d.polygon([p(0.18, 0.22, z), p(0.58, 0.22, z), p(0.58, 0.6, z), p(0.18, 0.6, z)], fill=(176, 184, 196, 255), outline=(104, 112, 126, 255))
    d.polygon([p(0.24, 0.28, z), p(0.52, 0.28, z), p(0.52, 0.54, z), p(0.24, 0.54, z)], fill=(132, 142, 158, 255))
    f = p(0.36, 0.16, z)
    d.line([f, (f[0], f[1] - 7), (f[0] + 3, f[1] - 6)], fill=(214, 220, 230, 255), width=2)
    d.point((f[0] + 4, f[1] - 4), fill=OL)
    for k in range(3):  # rak pinggan
        q = p(0.66 + k * 0.08, 0.5, z)
        d.ellipse([q[0] - 2, q[1] - 7, q[0] + 1, q[1]], fill=(250, 250, 252, 255), outline=OL)
    m = p(0.7, 0.82, z)
    d.rectangle([m[0] - 2, m[1] - 4, m[0] + 1, m[1]], fill=G_RED, outline=OL)
    return img


def pattern_tile(fn, edge=None):
    """Jubin lantai 56x28 (bentuk sama floor_tile); fn(u, v, x, y) -> warna untuk setiap piksel."""
    img, d = new(56, 28)
    pts = [(28, 0), (55, 14), (28, 27), (0, 14)]
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.polygon(pts, outline=(255, 255, 255, 255))  # liputan piksel sama floor_tile (tiada celah antara jubin)
    px = img.load()
    for y in range(28):
        for x in range(56):
            if px[x, y][3]:
                a, b = (x + 0.5 - 28) / 28, (y + 0.5) / 14
                u = min(max((a + b) / 2, 0.0), 0.999)
                v = min(max((b - a) / 2, 0.0), 0.999)
                px[x, y] = fn(u, v, x, y)
    if edge:
        d.polygon(pts, outline=edge)
    return img


def tint_add(color, k):
    return tuple(max(0, min(255, c + k)) for c in color[:3]) + (255,)


def deck_tile(variant):
    """Dek kayu luar kelabu-perang: 4 papan sepanjang paksi c setiap tile, sambungan berselang."""
    base = (150, 128, 106) if variant == 'a' else (140, 119, 98)
    seam = (92, 76, 62, 255)
    tones = [[0, -5], [6, 1], [-4, 3], [3, -3]]
    rnd = random.Random(31 if variant == 'a' else 32)
    grain = {(rnd.randint(0, 55), rnd.randint(0, 27)) for _ in range(60)}

    def fn(u, v, x, y):
        k = min(3, int(v * 4))
        fv = v * 4 - k
        if fv < 0.15:
            return seam
        off = 0.0 if k % 2 == 0 else 0.5
        du = (u - off) % 1.0
        if du < 0.026:
            return seam
        col = tint_add(base, tones[k][0 if u < off or (off == 0.0) else 1])
        if fv < 0.32:
            col = tint_add(col, 12)
        elif fv > 0.86:
            col = tint_add(col, -10)
        if (x, y) in grain:
            col = tint_add(col, -12)
        return col
    return pattern_tile(fn)


def grass_tile(variant):
    """Rumput: dua tona (jalur mesin rumput) dengan bilah terang/gelap rawak."""
    base = (110, 172, 74) if variant == 'a' else (98, 158, 64)
    rnd = random.Random(41 if variant == 'a' else 42)
    noise = {(x, y): rnd.random() for y in range(28) for x in range(56)}

    def fn(u, v, x, y):
        r = noise[(x, y)]
        if r < 0.14:
            return tint_add(base, 20)
        if r < 0.27:
            return tint_add(base, -16)
        if r < 0.30 and noise.get((x, y + 1), 1) < 0.5:
            return tint_add(base, 30)
        return base + (255,)
    return pattern_tile(fn)


def carpet_tile(variant):
    """Permaidani pejabat eksekutif kelabu-biru, tekstur halus + garis jubin karpet samar."""
    base = (122, 134, 156) if variant == 'a' else (114, 126, 148)
    rnd = random.Random(51 if variant == 'a' else 52)
    noise = {(x, y): rnd.random() for y in range(28) for x in range(56)}

    def fn(u, v, x, y):
        col = base + (255,)
        if (x + 2 * y) % 4 == 0:
            col = tint_add(col, -5)
        r = noise[(x, y)]
        if r < 0.08:
            col = tint_add(col, 7)
        elif r < 0.14:
            col = tint_add(col, -7)
        return col
    return pattern_tile(fn, edge=tint_add(base, -12))


def multifloor_assets():
    out = {
        'stairs': stairs(), 'stair_hut': stair_hut(), 'training_desk': training_desk(),
        'projector_screen': projector_screen(), 'whiteboard': whiteboard(), 'coffee_table': coffee_table(),
        'exec_desk': exec_desk(), 'glass_a': glass_wall(), 'glass_b': glass_wall().transpose(Image.FLIP_LEFT_RIGHT),
        'arcade': arcade(), 'tv_console': tv_console(),
        **{f'beanbag_{name}': beanbag(color) for name, color in GOOGLE.items()},
        'umbrella_table': umbrella_table(), 'lounger': lounger(), 'bbq': bbq(), 'planter': planter(),
        'outdoor_desk': outdoor_desk(), 'ac_unit': ac_unit(), 'pantry_counter': pantry_counter(),
        'railing_a': railing(), 'railing_b': railing().transpose(Image.FLIP_LEFT_RIGHT),
        'deck_a': deck_tile('a'), 'deck_b': deck_tile('b'), 'grass_a': grass_tile('a'), 'grass_b': grass_tile('b'),
        'carpet_a': carpet_tile('a'), 'carpet_b': carpet_tile('b'),
    }
    return out


def make_multifloor_preview(folder, assets, base):
    """Preview sprite baharu: grid, dan satu adegan ujian (checker lantai, dinding kaca, pagar, tangga)."""
    folder.mkdir(parents=True, exist_ok=True)
    names = [n for n in assets if not n.split('_')[0] in ('deck', 'grass', 'carpet')]
    cols, cell_w, cell_h = 6, 80, 120
    sheet = Image.new('RGBA', (cols * cell_w, ((len(names) + cols - 1) // cols) * cell_h), (190, 140, 90, 255))
    for i, name in enumerate(names):
        img = assets[name]
        sheet.alpha_composite(img, ((i % cols) * cell_w + (cell_w - img.width) // 2, (i // cols) * cell_h + cell_h - img.height - 4))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(folder / 'preview_multifloor.png')

    # Adegan: 12 x 9 grid. Zon: kayu (floor), karpet, dek, rumput.
    gc, gr = 12, 9
    W, Hh = (gc + gr) * 28 + 40, (gc + gr) * 14 + 160
    ox, oy = gr * 28 + 20, 130
    scene = Image.new('RGBA', (W, Hh), (60, 64, 72, 255))
    center = lambda c, r: (ox + (c - r) * 28, oy + (c + r) * 14)

    def tile_kind(c, r):
        if c >= 8 and r >= 5:
            return 'grass'
        if c >= 8 or r >= 6:
            return 'deck'
        if c <= 3 and r <= 3:
            return 'carpet'
        return 'floor'
    for r in range(gr):
        for c in range(gc):
            k = tile_kind(c, r)
            t = (base if k == 'floor' else assets)[f'{k}_{"a" if (c + r) % 2 == 0 else "b"}']
            x, y = center(c, r)
            scene.alpha_composite(t, (x - 28, y - 14))
    items = []
    for c in range(0, 4):
        items.append(('glass_a', c, 4))
    for r in range(0, 4):
        items.append(('glass_b', 4, r))
    items += [('exec_desk', 1, 1), ('chair_blue', 1, 2), ('stairs', 6, 2), ('arcade', 5, 0), ('tv_console', 7, 0),
              ('beanbag_red', 6, 4), ('beanbag_yellow', 7, 4), ('coffee_table', 2, 6), ('whiteboard', 5, 5),
              ('projector_screen', 6, 5), ('training_desk', 3, 7), ('outdoor_desk', 1, 7),
              ('umbrella_table', 9, 2), ('lounger', 10, 3), ('bbq', 10, 6), ('planter', 9, 7), ('ac_unit', 11, 1),
              ('stair_hut', 10, 0), ('pantry_counter', 0, 5), ('chair_green', 3, 8)]
    for c in range(gc):
        items.append(('railing_a', c, gr - 1))
    for r in range(gr):
        items.append(('railing_b', gc - 1, r))
    extra = {'chair_blue': chair(G_BLUE), 'chair_green': chair(G_GREEN)}
    for kind, c, r in sorted(items, key=lambda t: (t[1] + t[2], t[0].startswith('railing'))):
        img = assets.get(kind) or extra[kind]
        x, y = center(c, r)
        scene.alpha_composite(img, (x - img.width // 2, y + 14 - img.height))
    scene.resize((W * 2, Hh * 2), Image.NEAREST).save(folder / 'preview_multifloor_scene.png')


# ---------------------------------------------------------------- rooftop: kolam, taman, parti; auditorium
# Sprite tambahan untuk dek kolam, taman, ruang parti dan auditorium. Gaya dan pembantu sama seperti di atas.

STONE = dict(top=(206, 200, 188, 255), left=(170, 164, 152, 255), right=(138, 132, 122, 255), hi=(232, 228, 218, 255))
CHROME = (222, 230, 240, 255)
CHROME_D = (150, 160, 178, 255)
NAVY = (28, 36, 82, 255)


def cyl(d, cx, cy, rx, ry, h, top, side, ol=OL):
    """Silinder: elips tapak berpusat (cx, cy), tinggi h, atas elips lebih cerah."""
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=side, outline=ol)
    d.rectangle([cx - rx, cy - h, cx + rx, cy], fill=side)
    d.line([(cx - rx, cy - h), (cx - rx, cy)], fill=ol)
    d.line([(cx + rx, cy - h), (cx + rx, cy)], fill=ol)
    d.ellipse([cx - rx, cy - h - ry, cx + rx, cy - h + ry], fill=top, outline=ol)


def star_pts(cx, cy, ro, ri, rot=-90):
    out = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        r = ro if i % 2 == 0 else ri
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def rocket_img(scale=1, angle=-40):
    """Roket Google-colour: badan putih, hidung/sirip merah, tingkap biru, api kuning. Dipusing ke kanan atas."""
    lay, d = new(10, 25)
    d.polygon([(2, 8), (4, 1), (5, 1), (7, 8)], fill=G_RED)
    d.rectangle([2, 8, 7, 18], fill=(248, 248, 250, 255))
    d.line([(7, 8), (7, 18)], fill=(200, 204, 214, 255))
    d.rectangle([3, 10, 6, 13], fill=G_BLUE)
    d.point((3, 10), fill=(190, 220, 255, 255))
    d.polygon([(2, 14), (0, 20), (2, 18)], fill=G_RED)
    d.polygon([(7, 14), (9, 20), (7, 18)], fill=G_RED)
    d.rectangle([3, 19, 6, 19], fill=(150, 156, 170, 255))
    d.polygon([(3, 20), (6, 20), (4, 24), (5, 24)], fill=G_YELLOW)
    d.polygon([(4, 20), (5, 20), (4, 22)], fill=(255, 150, 40, 255))
    outline_alpha(lay)
    if scale != 1:
        lay = lay.resize((round(lay.width * scale), round(lay.height * scale)), Image.NEAREST)
    return lay.rotate(angle, expand=True, resample=Image.NEAREST)


def text_size(text, size):
    from PIL import ImageFont
    return ImageFont.load_default(size=size).getbbox(text)


# ---- kolam: jubin air ------------------------------------------------------------------------------
def water_tile(variant):
    """Air kolam turquoise dengan riak terang lembut; tepi nipis lebih gelap (sama bentuk deck_a)."""
    base = (64, 204, 224) if variant == 'a' else (56, 194, 218)
    rnd = random.Random(61 if variant == 'a' else 62)
    light, soft, dark = set(), set(), set()
    for _ in range(11):
        x, y = rnd.randint(8, 46), rnd.randint(5, 22)
        n = rnd.randint(3, 6)
        for i in range(n):
            light.add((x + i, y))
        for i in range(1, n - 1):
            soft.add((x - 1 + i, y + 1))
        for i in range(n):
            dark.add((x + 2 + i, y + 3))
    sparkle = {(rnd.randint(8, 46), rnd.randint(5, 22)) for _ in range(5)}

    def fn(u, v, x, y):
        w = math.sin((u + v) * 8.0 + (0 if variant == 'a' else 1.7)) + math.sin((u - v) * 6.0 + 0.8)
        col = tint_add(base, int(w * 3.2) + int((0.5 - abs(u - 0.5) - abs(v - 0.5)) * 8))
        if (x, y) in dark and (x, y) not in light:
            col = tint_add(col, -12)
        if (x, y) in soft:
            col = tint_add(col, 10)
        if (x, y) in light:
            col = tint_add(col, 26)
        if (x, y) in sparkle:
            col = (232, 250, 255, 255)
        return col
    return pattern_tile(fn, edge=tint_add(base, -11))


def pool_ladder():
    """Tangga kolam krom: dua rel melengkung di tepi dek, anak tangga turun ke air (riak di kaki)."""
    H = 60
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ring, rd = new(56, H)
    q = p(0.5, 0.74, 0)
    rd.ellipse([q[0] - 14, q[1] - 5, q[0] + 14, q[1] + 5], outline=(214, 248, 255, 190))
    rd.ellipse([q[0] - 8, q[1] - 3, q[0] + 8, q[1] + 3], outline=(214, 248, 255, 140))
    img.alpha_composite(ring)
    for u in (0.3, 0.7):
        flange = [p(u - 0.09, 0.08, 0), p(u + 0.09, 0.08, 0), p(u + 0.09, 0.2, 0), p(u - 0.09, 0.2, 0)]
        d.polygon(flange, fill=CHROME_D, outline=OL)
    rails = {}
    for u in (0.3, 0.7):
        rails[u] = [p(u, 0.14, 1), p(u, 0.14, 27), p(u, 0.26, 34), p(u, 0.46, 32), p(u, 0.74, 3)]
    for u in (0.3, 0.7):
        d.line(rails[u], fill=OL, width=4)
    for z in (9, 16, 23):  # anak tangga antara dua rel (di bahagian turun)
        t = (32 - z) / 29
        v = 0.46 + (0.74 - 0.46) * t
        d.line([p(0.3, v, z), p(0.7, v, z)], fill=OL, width=3)
        d.line([p(0.3, v, z), p(0.7, v, z)], fill=CHROME_D, width=1)
    for u in (0.3, 0.7):
        d.line(rails[u], fill=CHROME, width=2)
        d.line([(x - 1, y - 1) for x, y in rails[u][1:4]], fill=(255, 255, 255, 255), width=1)
    d.point(p(0.7, 0.74, 3), fill=(190, 240, 250, 255))
    return img


def diving_board():
    """Papan lompat: tapak putih/biru dan papan fleksibel bertekstur menjulur ke arah +c."""
    H = 56
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ibox(d, H, 0.0, 0.34, 0.3, 0.7, 0, 13, (240, 244, 248, 255), (222, 228, 238, 255), (176, 186, 202, 255), (255, 255, 255, 255))
    a = p(0.17, 0.7, 7)
    d.rectangle([a[0] - 3, a[1], a[0] + 3, a[1] + 2], fill=G_BLUE)
    z0, z1 = 13, 16
    ibox(d, H, 0.12, 1.02, 0.38, 0.62, z0, z1, (252, 252, 252, 255), (210, 224, 244, 255), (150, 178, 222, 255), (255, 255, 255, 255))
    for k in range(5):  # jalur tekstur biru pada papan
        u = 0.34 + k * 0.14
        d.line([p(u, 0.4, z1), p(u, 0.6, z1)], fill=G_BLUE)
    for v in (0.34, 0.66):  # susur pendek di pangkal papan
        d.line([p(0.06, v, 13), p(0.06, v, 24)], fill=OL, width=3)
        d.line([p(0.06, v, 13), p(0.06, v, 24)], fill=CHROME, width=1)
    d.line([p(0.06, 0.34, 24), p(0.06, 0.66, 24)], fill=OL, width=3)
    d.line([p(0.06, 0.34, 24), p(0.06, 0.66, 24)], fill=CHROME, width=1)
    return img


def garden_tree():
    """Pokok rendang dalam tapak penanam batu bulat bertanah mulsa."""
    H = 96
    img, d = new(56, H)
    cx, cy = 28, H - 14
    cyl(d, cx, cy, 25, 12, 8, STONE['top'], STONE['left'])
    d.arc([cx - 25, cy - 12, cx + 25, cy + 12], 20, 160, fill=STONE['right'])
    d.line([(cx - 24, cy - 3), (cx - 3, cy + 7)], fill=STONE['hi'])
    soil = (98, 64, 42, 255)
    d.ellipse([cx - 21, cy - 17, cx + 21, cy + 1], fill=soil, outline=(60, 40, 26, 255))
    rnd = random.Random(71)
    for _ in range(40):
        x, y = rnd.randint(cx - 18, cx + 18), rnd.randint(cy - 14, cy)
        if img.getpixel((x, y)) == soil:
            d.point((x, y), fill=(128, 88, 58, 255) if rnd.random() < 0.5 else (70, 46, 30, 255))
    bark = (118, 80, 52, 255)
    d.polygon([(24, cy - 6), (32, cy - 6), (31, cy - 36), (26, cy - 36)], fill=bark, outline=OL)
    d.line([(28, cy - 8), (28, cy - 34)], fill=(146, 104, 72, 255))
    d.line([(27, cy - 30), (16, cy - 44)], fill=OL, width=3)
    d.line([(29, cy - 30), (41, cy - 44)], fill=OL, width=3)
    d.line([(27, cy - 30), (16, cy - 44)], fill=bark, width=1)
    d.line([(29, cy - 30), (41, cy - 44)], fill=bark, width=1)
    fol, fd = new(56, H)
    dark, mid, light = (46, 110, 52, 255), (76, 150, 66, 255), (128, 192, 96, 255)
    blobs = ((28, 34, 17), (13, 42, 12), (43, 42, 12), (18, 24, 12), (38, 23, 12), (28, 14, 12), (8, 30, 7), (49, 30, 7))
    for (x, y, r) in blobs:
        fd.ellipse([x - r, y - r, x + r, y + r], fill=mid)
    for (x, y, r) in blobs:
        fd.pieslice([x - r, y - r, x + r, y + r], 20, 160, fill=dark)
    for (x, y, r) in blobs:
        fd.ellipse([x - r + 3, y - r + 2, x + r - 4, y + r - 7], fill=mid)
        fd.ellipse([x - r + 4, y - r + 3, x + 1, y - 1], fill=light)
    for _ in range(80):
        x, y = rnd.randint(4, 52), rnd.randint(2, 56)
        if fol.getpixel((x, y))[3]:
            fd.rectangle([x, y, x + 1, y], fill=light if rnd.random() < 0.55 else dark)
    for (x, y) in ((14, 34), (30, 18), (40, 36), (22, 44), (34, 28)):  # bunga/buah kecil
        if fol.getpixel((x, y))[3]:
            fd.rectangle([x, y, x + 1, y + 1], fill=(250, 232, 242, 255) if (x + y) % 2 else G_YELLOW)
    outline_alpha(fol, (30, 70, 38, 255))
    img.alpha_composite(fol)
    return img


def flower_bed():
    """Batas bunga batu tinggi: tanah gelap, daun hijau, bunga warna Google, merah jambu dan putih."""
    H = 40
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ibox(d, H, 0.04, 0.96, 0.04, 0.96, 0, 10, STONE['top'], STONE['left'], STONE['right'], STONE['hi'])
    d.line([p(0.05, 0.96, 5), p(0.95, 0.96, 5)], fill=shade(STONE['left'], 0.8))
    d.line([p(0.96, 0.95, 5), p(0.96, 0.05, 5)], fill=shade(STONE['right'], 0.8))
    for u in (0.3, 0.55, 0.8):
        d.line([p(u, 0.96, 0), p(u, 0.96, 4)], fill=shade(STONE['left'], 0.8))
        d.line([p(u - 0.12, 0.96, 5), p(u - 0.12, 0.96, 10)], fill=shade(STONE['left'], 0.8))
    for v in (0.2, 0.45, 0.7):
        d.line([p(0.96, v, 0), p(0.96, v, 4)], fill=shade(STONE['right'], 0.8))
        d.line([p(0.96, v + 0.12, 5), p(0.96, v + 0.12, 10)], fill=shade(STONE['right'], 0.8))
    d.polygon([p(0.12, 0.12, 10), p(0.88, 0.12, 10), p(0.88, 0.88, 10), p(0.12, 0.88, 10)], fill=(92, 62, 42, 255), outline=OL)
    fol, fd = new(56, H)
    rnd = random.Random(77)
    green, lgreen = (64, 138, 62, 255), (112, 178, 88, 255)
    spots = []
    for _ in range(22):
        u, v = rnd.uniform(0.2, 0.8), rnd.uniform(0.2, 0.8)
        x, y = p(u, v, 10)
        spots.append((x, y, u + v))
    spots.sort(key=lambda s: s[2])
    cols = [G_RED, G_YELLOW, (255, 255, 255, 255), (244, 143, 177, 255), G_BLUE, (186, 104, 200, 255), G_RED, G_YELLOW]
    for (x, y, _) in spots:
        h = rnd.randint(3, 8)
        fd.ellipse([x - 3, y - 4, x + 3, y], fill=green)
        fd.line([(x, y - 2), (x, y - h)], fill=lgreen)
    outline_alpha(fol, (30, 70, 38, 255))
    img.alpha_composite(fol)
    for i, (x, y, _) in enumerate(spots):
        h = 3 + (i * 5) % 6
        col = cols[i % len(cols)]
        bx, by = x, y - h - 2
        d.rectangle([bx - 1, by - 1, bx + 1, by + 1], fill=col, outline=OL)
        d.point((bx, by), fill=(255, 238, 160, 255) if col != G_YELLOW else (255, 255, 255, 255))
    return img


def fountain():
    """Air pancut taman batu: kolam bulat, tiang tengah, mangkuk atas, air memancut dan menitis."""
    H = 64
    img, d = new(56, H)
    cx, cy = 28, H - 14
    cyl(d, cx, cy, 26, 13, 10, (118, 214, 232, 255), STONE['left'])
    d.arc([cx - 26, cy - 13, cx + 26, cy + 13], 20, 160, fill=STONE['right'])
    d.ellipse([cx - 22, cy - 20, cx + 22, cy - 1], fill=(88, 202, 224, 255), outline=(60, 150, 176, 255))
    d.ellipse([cx - 16, cy - 17, cx + 16, cy - 5], outline=(168, 236, 248, 255))
    d.line([(cx - 25, cy - 4), (cx - 4, cy + 6)], fill=STONE['hi'])
    d.rectangle([cx - 3, cy - 30, cx + 3, cy - 10], fill=STONE['left'], outline=OL)
    d.line([(cx - 1, cy - 29), (cx - 1, cy - 11)], fill=STONE['hi'])
    d.ellipse([cx - 4, cy - 14, cx + 4, cy - 8], fill=STONE['top'], outline=OL)
    cyl(d, cx, cy - 30, 12, 6, 4, (118, 214, 232, 255), STONE['left'])
    d.ellipse([cx - 9, cy - 36, cx + 9, cy - 30], fill=(88, 202, 224, 255))
    wat = (186, 240, 252, 255)
    d.line([(cx, cy - 34), (cx, cy - 46)], fill=wat, width=2)
    d.line([(cx, cy - 46), (cx - 6, cy - 40), (cx - 10, cy - 32)], fill=wat)
    d.line([(cx, cy - 46), (cx + 6, cy - 40), (cx + 10, cy - 32)], fill=wat)
    d.point((cx, cy - 48), fill=(255, 255, 255, 255))
    for x in (cx - 10, cx - 6, cx - 2, cx + 3, cx + 7, cx + 11):
        d.line([(x, cy - 28), (x, cy - 19)], fill=(150, 226, 244, 255))
    for x, y in ((cx - 12, cy - 17), (cx + 1, cy - 16), (cx + 12, cy - 18), (cx - 5, cy - 14), (cx + 6, cy - 13)):
        d.point((x, y), fill=(236, 252, 255, 255))
    return img


# ---- parti ------------------------------------------------------------------------------------------
def dj_booth():
    """Booth DJ: meja gelap dengan dua turntable dan mixer, speaker dengan LED warna Google, panel EQ di belakang."""
    H = 76
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    blk = dict(top=(52, 54, 68, 255), left=(36, 38, 50, 255), right=(26, 28, 38, 255), hi=(96, 100, 122, 255))
    d.polygon([p(0.05, 0.06, 20), p(0.95, 0.06, 20), p(0.95, 0.06, 46), p(0.05, 0.06, 46)], fill=(16, 18, 34, 255), outline=OL)
    bars = [(G_BLUE, 8), (G_RED, 14), (G_YELLOW, 10), (G_GREEN, 18), (G_BLUE, 12), (G_RED, 16), (G_YELLOW, 9), (G_GREEN, 13)]
    for i, (col, h) in enumerate(bars):
        u = 0.12 + i * 0.105
        d.line([p(u, 0.06, 23), p(u, 0.06, 23 + h)], fill=col, width=2)
    for (u0, u1, v0, v1, face) in ((0.0, 0.36, 0.64, 1.0, 'L'), (0.64, 1.0, 0.0, 0.36, 'R')):
        ibox(d, H, u0, u1, v0, v1, 0, 38, blk['top'], blk['left'], blk['right'], blk['hi'])
        fl, fd = new(11, 24)
        fd.ellipse([0, 8, 10, 18], fill=(24, 26, 34, 255), outline=(110, 114, 132, 255))
        fd.ellipse([3, 11, 7, 15], fill=(70, 74, 92, 255))
        fd.ellipse([3, 0, 7, 4], fill=(24, 26, 34, 255), outline=(110, 114, 132, 255))
        for i, col in enumerate((G_BLUE, G_RED, G_YELLOW, G_GREEN)):
            fd.point((1 + i * 2, 21), fill=col)
        if face == 'L':
            x0, y0 = p(0.05, 1.0, 36)
            paste_L(img, fl, x0, y0)
        else:
            x0, y0 = p(1.0, 0.36, 36)
            paste_R(img, fl, x0, y0)
    ibox(d, H, 0.24, 0.76, 0.3, 0.7, 0, 18, blk['top'], blk['left'], blk['right'], blk['hi'])
    d.line([p(0.26, 0.7, 14), p(0.74, 0.7, 14)], fill=G_BLUE)
    d.line([p(0.76, 0.68, 14), p(0.76, 0.32, 14)], fill=G_RED)
    d.line([p(0.26, 0.7, 6), p(0.74, 0.7, 6)], fill=shade(G_YELLOW, 0.9))
    for (u, v) in ((0.36, 0.6), (0.64, 0.4)):
        x, y = p(u, v, 18)
        d.ellipse([x - 6, y - 3, x + 6, y + 3], fill=(150, 154, 168, 255), outline=OL)
        d.ellipse([x - 5, y - 3, x + 4, y + 2], fill=(18, 18, 24, 255))
        d.ellipse([x - 3, y - 2, x + 2, y + 1], fill=G_RED)
        d.point((x, y - 1), fill=(255, 255, 255, 255))
        d.line([(x + 6, y - 3), (x + 2, y)], fill=(210, 214, 224, 255))
    x, y = p(0.5, 0.5, 18)
    d.rectangle([x - 3, y - 4, x + 3, y], fill=(38, 40, 52, 255), outline=OL)
    for i, col in enumerate((G_GREEN, G_YELLOW, G_RED)):
        d.point((x - 2 + i * 2, y - 3), fill=col)
    d.arc([x + 9, y - 9, x + 17, y - 1], 180, 360, fill=OL)
    d.rectangle([x + 8, y - 4, x + 9, y - 2], fill=G_BLUE)
    d.rectangle([x + 16, y - 4, x + 17, y - 2], fill=G_BLUE)
    return img


def bar_counter():
    """Kaunter bar parti: kayu gelap, jalur LED, botol dan paip draf, dua bangku berkusyen warna Google."""
    H = 64
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    ibox(d, H, 0.0, 1.0, 0.08, 0.34, 0, 20, WALNUT['top'], WALNUT['left'], WALNUT['right'], WALNUT['hi'])
    d.line([p(0.04, 0.34, 4), p(0.96, 0.34, 4)], fill=GOLD)
    d.line([p(1.0, 0.32, 4), p(1.0, 0.1, 4)], fill=shade(GOLD, 0.75))
    for (u, col, h) in ((0.12, G_GREEN, 9), (0.24, G_RED, 11), (0.36, (150, 100, 50, 255), 8), (0.8, G_YELLOW, 10), (0.92, G_BLUE, 8)):
        x, y = p(u, 0.22, 20)
        d.rectangle([x - 2, y - h + 3, x + 1, y], fill=shade(col, 0.9), outline=OL)
        d.rectangle([x - 1, y - h - 2, x, y - h + 3], fill=shade(col, 0.9), outline=OL)
        d.point((x - 1, y - h - 3), fill=(220, 224, 232, 255))
        d.line([(x - 1, y - h + 5), (x - 1, y - 2)], fill=shade(col, 1.4))
    x, y = p(0.55, 0.22, 20)
    d.rectangle([x - 1, y - 8, x + 1, y], fill=CHROME, outline=OL)
    d.line([(x - 1, y - 9), (x + 6, y - 9)], fill=OL, width=3)
    d.line([(x - 1, y - 9), (x + 6, y - 9)], fill=CHROME, width=1)
    d.rectangle([x + 5, y - 7, x + 6, y - 5], fill=(190, 196, 208, 255), outline=OL)
    x -= 0
    d.rectangle([x + 4, y - 14, x + 7, y - 9], fill=G_RED, outline=OL)
    ibox(d, H, 0.0, 1.0, 0.42, 0.74, 0, 22, (60, 40, 30, 255), (92, 60, 42, 255), (66, 42, 30, 255), (150, 112, 82, 255))
    d.line([p(0.02, 0.74, 20), p(0.98, 0.74, 20)], fill=GOLD)
    d.line([p(1.0, 0.72, 20), p(1.0, 0.44, 20)], fill=shade(GOLD, 0.8))
    seg = [G_BLUE, G_RED, G_YELLOW, G_GREEN]
    for i, col in enumerate(seg):
        u0, u1 = 0.04 + i * 0.235, 0.04 + (i + 1) * 0.235 - 0.02
        d.line([p(u0, 0.74, 5), p(u1, 0.74, 5)], fill=col, width=2)
    d.line([p(1.0, 0.7, 5), p(1.0, 0.46, 5)], fill=G_BLUE, width=2)
    for u in (0.25, 0.5, 0.75):
        d.line([p(u, 0.74, 9), p(u, 0.74, 17)], fill=(70, 46, 32, 255))
    for (u, v, col) in ((0.4, 0.58, (255, 255, 255, 200)), (0.7, 0.62, (250, 196, 190, 220))):
        x, y = p(u, v, 22)
        d.rectangle([x - 2, y - 4, x + 1, y], fill=col, outline=OL)
    for u, col in ((0.26, G_RED), (0.72, G_YELLOW)):
        x, y = p(u, 0.98, 0)
        d.line([(x, y - 11), (x, y - 1)], fill=CHROME_D, width=2)
        d.ellipse([x - 5, y - 2, x + 5, y + 1], fill=CHROME_D, outline=OL)
        d.ellipse([x - 6, y - 15, x + 6, y - 9], fill=shade(col, 0.7), outline=OL)
        d.ellipse([x - 6, y - 17, x + 6, y - 11], fill=col, outline=OL)
        d.arc([x - 4, y - 16, x + 3, y - 13], 200, 290, fill=shade(col, 1.3))
    return img


def balloons():
    """Sekumpulan belon warna Google diikat pada pemberat emas."""
    H = 80
    img, d = new(56, H)
    wx, wy = 28, H - 16
    cluster = [(14, 34, G_GREEN), (42, 34, G_YELLOW), (28, 29, G_RED), (19, 20, G_BLUE), (37, 20, G_RED), (28, 10, G_BLUE)]
    for (x, y, col) in cluster:
        d.line([(x, y + 11), (wx, wy - 5)], fill=(210, 214, 222, 255))
    for (x, y, col) in sorted(cluster, key=lambda t: -t[1]):
        layer, ld = new(56, H)
        ld.ellipse([x - 7, y - 9, x + 7, y + 9], fill=col)
        ld.polygon([(x - 2, y + 9), (x + 2, y + 9), (x, y + 12)], fill=shade(col, 0.78))
        ld.chord([x - 6, y - 5, x + 6, y + 9], 20, 160, fill=shade(col, 0.88))
        ld.ellipse([x - 4, y - 7, x - 2, y - 4], fill=shade(col, 1.45))
        ld.point((x - 3, y - 3), fill=(255, 255, 255, 255))
        outline_alpha(layer)
        img.alpha_composite(layer)
    ibox(d, H, 0.34, 0.66, 0.34, 0.66, 0, 7, (232, 194, 90, 255), (214, 172, 72, 255), (170, 130, 50, 255), (252, 226, 150, 255))
    d.line([isop(H, 0.34, 0.66, 3), isop(H, 0.66, 0.66, 3)], fill=G_RED)
    d.line([isop(H, 0.66, 0.66, 3), isop(H, 0.66, 0.34, 3)], fill=shade(G_RED, 0.8))
    return img


def party_table():
    """Meja koktel tinggi: bulat, kaki langsing, snek dan minuman berwarna."""
    H = 56
    img, d = new(56, H)
    cx, cy = 28, H - 14
    d.ellipse([cx - 9, cy - 4, cx + 9, cy + 4], fill=(150, 156, 170, 255), outline=OL)
    d.ellipse([cx - 6, cy - 4, cx + 6, cy + 1], fill=(196, 202, 214, 255))
    d.rectangle([cx - 1, cy - 33, cx + 1, cy - 2], fill=(170, 176, 190, 255), outline=OL)
    d.line([(cx - 1, cy - 31), (cx - 1, cy - 4)], fill=(236, 240, 248, 255))
    ty = cy - 34
    d.ellipse([cx - 16, ty - 5, cx + 16, ty + 11], fill=(116, 66, 160, 255), outline=OL)
    d.ellipse([cx - 16, ty - 8, cx + 16, ty + 6], fill=(250, 248, 244, 255), outline=OL)
    d.arc([cx - 13, ty - 6, cx + 12, ty + 4], 195, 290, fill=(255, 255, 255, 255))
    d.ellipse([cx - 11, ty - 3, cx - 3, ty + 2], fill=(230, 232, 238, 255), outline=OL)
    for (x, y, col) in ((cx - 9, ty - 4, G_YELLOW), (cx - 6, ty - 5, (240, 170, 50, 255)), (cx - 4, ty - 3, G_YELLOW), (cx - 7, ty - 2, (240, 170, 50, 255))):
        d.rectangle([x, y, x + 1, y + 1], fill=col)
    for (x, col) in ((cx + 2, G_RED), (cx + 8, G_BLUE)):
        d.rectangle([x - 2, ty - 8, x + 2, ty - 1], fill=col, outline=OL)
        d.line([(x - 1, ty - 7), (x - 1, ty - 4)], fill=shade(col, 1.4))
        d.line([(x + 1, ty - 11), (x + 1, ty - 8)], fill=(250, 250, 250, 255), width=1)
    d.rectangle([cx - 1, ty + 1, cx + 3, ty + 4], fill=(255, 255, 255, 255), outline=OL)
    d.point((cx + 1, ty + 2), fill=G_GREEN)
    d.point((cx + 2, ty + 3), fill=G_RED)
    return img


# ---- auditorium ---------------------------------------------------------------------------------------
def stage_tile():
    """Pentas tinggi: tepi hadapan kayu, atas permaidani gelap; baris tile membentuk pentas."""
    H = 44
    img, d = new(56, H)
    cx, cy, h = 28, H - 14, 14
    wl, wr = (176, 124, 80, 255), (130, 88, 54, 255)
    d.polygon([(cx - 28, cy - h), (cx, cy - h + 14), (cx, cy + 14), (cx - 28, cy)], fill=wl, outline=OL)
    d.polygon([(cx + 28, cy - h), (cx, cy - h + 14), (cx, cy + 14), (cx + 28, cy)], fill=wr, outline=OL)
    for z in (4, 9):
        d.line([(cx - 27, cy - z), (cx - 1, cy - z + 14)], fill=shade(wl, 0.78))
        d.line([(cx + 27, cy - z), (cx + 1, cy - z + 14)], fill=shade(wr, 0.78))
    d.line([(cx - 27, cy - h + 1), (cx - 1, cy - h + 15)], fill=(214, 168, 120, 255))
    carpet = (54, 56, 88, 255)
    top = [(cx, cy - h - 14), (cx + 28, cy - h), (cx, cy - h + 14), (cx - 28, cy - h)]
    d.polygon(top, fill=carpet, outline=shade(carpet, 0.78))
    px = img.load()
    rnd = random.Random(81)
    for y in range(H):
        for x in range(56):
            if px[x, y] == carpet:
                if (x + 2 * y) % 4 == 0:
                    px[x, y] = tint_add(carpet, -5)
                elif rnd.random() < 0.07:
                    px[x, y] = tint_add(carpet, 8)
    d.line([(cx - 25, cy - h), (cx - 1, cy - h + 12)], fill=G_YELLOW)
    d.line([(cx + 25, cy - h), (cx + 1, cy - h + 12)], fill=shade(G_YELLOW, 0.8))
    d.line([(cx - 27, cy - h), (cx - 1, cy - h + 14)], fill=OL)
    d.line([(cx + 27, cy - h), (cx + 1, cy - h + 14)], fill=OL)
    return img


def launch_flat(w, h, text_px=9):
    """Grafik 'launch' untuk skrin LED: langit ungu-biru, bintang, roket dan jejak warna Google."""
    fl, fd = new(w, h)
    for y in range(h):
        t = y / (h - 1)
        fd.line([(0, y), (w - 1, y)], fill=(int(24 + 40 * t), int(30 + 22 * t), int(86 + 44 * t), 255))
    rnd = random.Random(91)
    for _ in range(24):
        x, y = rnd.randint(1, w - 2), rnd.randint(1, h - 16)
        fd.point((x, y), fill=(255, 255, 255, 255) if rnd.random() < 0.6 else (160, 180, 240, 255))
    for i, col in enumerate((G_BLUE, G_RED, G_YELLOW, G_GREEN)):
        o = (i - 1.5) * 3
        fd.line([(6 + o, h - 18), (w * 0.5 + o, h * 0.4)], fill=col, width=2)
    r = rocket_img(1.5, -38)
    fl.alpha_composite(r, (int(w * 0.6) - r.width // 2, int(h * 0.34) - r.height // 2))
    fd.polygon(star_pts(8, 9, 5, 2), fill=G_YELLOW)
    x0, y0, x1, y1 = text_size('LAUNCH', text_px)
    tw = x1 - x0
    for dx in (0, 1):
        pixel_text(fl, ((w - tw) // 2 - x0 + dx, h - 13 - y0), 'LAUNCH', text_px, (255, 255, 255, 255))
    return fl


def stage_screen():
    """Skrin LED besar atas rangka, menghadap +r (satah selari paksi c, macam projector_screen)."""
    H = 110
    img, d = new(56, H)
    W, Hs = 52, 64
    x0, y0 = 2, H - 28 - 14 - Hs
    gy = lambda x: H - 28 + (x - 2) // 2
    for x in (8, 48):
        d.rectangle([x - 1, y0 + Hs + (x - 2) // 2 - 4, x + 1, gy(x)], fill=(60, 64, 76, 255), outline=OL)
        d.rectangle([x - 6, gy(x) - 1, x + 6, gy(x) + 2], fill=(80, 84, 96, 255), outline=OL)
    fl, fd = new(W, Hs)
    fd.rectangle([0, 0, W - 1, Hs - 1], fill=(40, 42, 52, 255), outline=OL)
    fd.rectangle([1, 1, W - 2, 2], fill=(86, 90, 104, 255))
    fl.alpha_composite(launch_flat(W - 6, Hs - 8), (3, 3))
    for y in range(4, Hs - 5, 2):
        for x in range(3, W - 3):
            r, g, b, a = fl.getpixel((x, y))
            fl.putpixel((x, y), (int(r * 0.9), int(g * 0.9), int(b * 0.92), a))
    fd.rectangle([2, Hs - 4, W - 3, Hs - 2], fill=(60, 64, 76, 255))
    for i, col in enumerate((G_BLUE, G_RED, G_YELLOW, G_GREEN)):
        fd.rectangle([W - 14 + i * 3, Hs - 3, W - 13 + i * 3, Hs - 3], fill=col)
    paste_L(img, fl, x0, y0)
    return img


def podium():
    """Podium kayu dengan permukaan condong, mikrofon gooseneck dan logo kecil di depan."""
    H = 64
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    wood = dict(top=(176, 124, 80, 255), left=(150, 102, 64, 255), right=(112, 76, 48, 255), hi=(208, 160, 116, 255))
    ibox(d, H, 0.12, 0.88, 0.22, 0.78, 0, 30, wood['top'], wood['left'], wood['right'], wood['hi'])
    d.polygon([p(0.1, 0.2, 34), p(0.9, 0.2, 34), p(0.9, 0.8, 30), p(0.1, 0.8, 30)], fill=(206, 160, 114, 255), outline=OL)
    d.polygon([p(0.1, 0.8, 30), p(0.9, 0.8, 30), p(0.9, 0.8, 28), p(0.1, 0.8, 28)], fill=(112, 76, 48, 255), outline=OL)
    d.polygon([p(0.9, 0.8, 30), p(0.9, 0.2, 34), p(0.9, 0.2, 32), p(0.9, 0.8, 28)], fill=wood['right'], outline=OL)
    d.polygon([p(0.2, 0.78, 4), p(0.8, 0.78, 4), p(0.8, 0.78, 26), p(0.2, 0.78, 26)], outline=shade(wood['left'], 0.72))
    fl, fd = new(9, 9)
    fd.pieslice([0, 0, 8, 8], 180, 270, fill=G_RED)
    fd.pieslice([0, 0, 8, 8], 270, 360, fill=G_YELLOW)
    fd.pieslice([0, 0, 8, 8], 0, 90, fill=G_GREEN)
    fd.pieslice([0, 0, 8, 8], 90, 180, fill=G_BLUE)
    fd.ellipse([2, 2, 6, 6], fill=(255, 255, 255, 255))
    x, y = p(0.5, 0.78, 20)
    paste_L(img, fl, x - 4, y - 4)
    mx, my = p(0.46, 0.4, 33)
    neck = [(mx, my), (mx - 1, my - 6), (mx + 2, my - 11), (mx + 5, my - 12)]
    d.line(neck, fill=OL, width=3)
    d.line(neck, fill=(120, 126, 140, 255), width=1)
    d.ellipse([mx + 4, my - 16, mx + 8, my - 11], fill=(40, 42, 50, 255), outline=OL)
    d.point((mx + 5, my - 15), fill=(160, 166, 180, 255))
    d.polygon([p(0.55, 0.42, 33), p(0.8, 0.42, 33), p(0.8, 0.7, 31), p(0.55, 0.7, 31)], fill=(250, 248, 238, 255), outline=OL)
    d.line([p(0.6, 0.5, 32), p(0.75, 0.5, 32)], fill=(170, 176, 190, 255))
    return img


def speaker_stack():
    """Menara speaker PA: subwoofer di bawah, speaker 2-hala di atas, LED hijau."""
    H = 70
    img, d = new(56, H)
    p = lambda u, v, z: isop(H, u, v, z)
    blk = dict(top=(62, 64, 78, 255), left=(40, 42, 54, 255), right=(28, 30, 40, 255), hi=(110, 114, 132, 255))
    ibox(d, H, 0.08, 0.92, 0.12, 0.88, 0, 22, blk['top'], blk['left'], blk['right'], blk['hi'])
    ibox(d, H, 0.18, 0.82, 0.22, 0.78, 22, 46, blk['top'], blk['left'], blk['right'], blk['hi'])
    fl, fd = new(22, 20)
    fd.ellipse([2, 1, 19, 18], fill=(20, 22, 30, 255), outline=(120, 126, 146, 255))
    fd.ellipse([6, 5, 15, 14], fill=(62, 66, 86, 255), outline=(20, 22, 30, 255))
    fd.ellipse([9, 8, 12, 11], fill=(120, 126, 146, 255))
    x0, y0 = p(0.12, 0.88, 21)
    paste_L(img, fl, x0, y0)
    fl2, fd2 = new(16, 22)
    fd2.ellipse([2, 8, 13, 19], fill=(20, 22, 30, 255), outline=(120, 126, 146, 255))
    fd2.ellipse([5, 11, 10, 16], fill=(62, 66, 86, 255))
    fd2.ellipse([5, 1, 10, 6], fill=(20, 22, 30, 255), outline=(120, 126, 146, 255))
    fd2.point((7, 3), fill=(150, 156, 176, 255))
    x0, y0 = p(0.22, 0.78, 45)
    paste_L(img, fl2, x0, y0 + 1)
    for z0 in (5, 28):
        d.line([p(0.92, 0.35, z0 + 8), p(0.92, 0.65, z0 + 8)], fill=(80, 84, 100, 255))
    d.line([p(0.92, 0.2, 2), p(0.92, 0.8, 2)], fill=G_BLUE)
    d.point(p(0.82, 0.7, 40), fill=G_GREEN)
    d.point(p(0.82, 0.62, 40), fill=G_RED)
    return img


def banner_flat(variant):
    """Sepanduk 84x40: jalur warna Google atas/bawah, panel navy, bintang atau roket, teks LAUNCH."""
    W, Hh = 84, 40
    fl, d = new(W, Hh)
    d.rectangle([0, 0, W - 1, Hh - 1], fill=(250, 250, 252, 255), outline=OL)
    d.rectangle([2, 2, W - 3, Hh - 3], fill=NAVY)
    seg = (G_BLUE, G_RED, G_YELLOW, G_GREEN) if variant == 'a' else (G_GREEN, G_YELLOW, G_RED, G_BLUE)
    for i in range(4):
        x0, x1 = 1 + i * 20, 1 + (i + 1) * 20 - (0 if i < 3 else 1)
        d.rectangle([x0, 1, x1, 4], fill=seg[i])
        d.rectangle([x0, Hh - 5, x1, Hh - 2], fill=seg[3 - i])
    rnd = random.Random(95 if variant == 'a' else 96)
    for _ in range(22):
        x, y = rnd.randint(3, W - 4), rnd.randint(6, Hh - 7)
        d.point((x, y), fill=(120, 134, 200, 255))
    size = 12
    bx0, by0, bx1, by1 = text_size('LAUNCH', size)
    tw, th = bx1 - bx0, by1 - by0
    if variant == 'a':
        d.polygon(star_pts(16, 21, 12, 5), fill=G_YELLOW, outline=OL)
        d.polygon(star_pts(16, 21, 7, 3), fill=(255, 226, 120, 255))
        tx = 31
    else:
        tx = 4
        r = rocket_img(1.15, -30)
        fl.alpha_composite(r, (W - 4 - r.width, (Hh - r.height) // 2 + 1))
        for i, col in enumerate((G_BLUE, G_RED, G_YELLOW)):
            d.line([(60 + i * 2, Hh - 8 - i * 2), (66 + i * 2, Hh - 14 - i * 2)], fill=col)
        d.polygon(star_pts(60, 11, 4, 2), fill=G_YELLOW)
    for dx in (0, 1):
        pixel_text(fl, (tx - bx0 + dx, (Hh - th) // 2 - by0), 'LAUNCH', size, (255, 255, 255, 255))
    for (gx, gy) in ((3, 6), (W - 4, 6), (3, Hh - 7), (W - 4, Hh - 7)):
        d.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=CHROME, outline=OL)
    return fl


def venue_assets():
    return {
        'water_a': water_tile('a'), 'water_b': water_tile('b'), 'pool_ladder': pool_ladder(),
        'diving_board': diving_board(), 'garden_tree': garden_tree(), 'flower_bed': flower_bed(), 'fountain': fountain(),
        'dj_booth': dj_booth(), 'bar_counter': bar_counter(), 'balloons': balloons(), 'party_table': party_table(),
        'stage': stage_tile(), 'stage_screen': stage_screen(), 'podium': podium(), 'speaker_stack': speaker_stack(),
        'wall_banner_a': shear(banner_flat('a'), 'A'), 'wall_banner_b': shear(banner_flat('b'), 'B'),
    }


def make_venue_preview(folder, assets, base, multi):
    """Preview kolam/parti/auditorium: grid sprite, adegan ujian, dan ujian checker air/dek."""
    folder.mkdir(parents=True, exist_ok=True)
    names = [n for n in assets if n.split('_')[0] != 'water']
    cols, cell_w, cell_h = 6, 100, 130
    sheet = Image.new('RGBA', (cols * cell_w, ((len(names) + cols - 1) // cols) * cell_h), (190, 140, 90, 255))
    for i, name in enumerate(names):
        img = assets[name]
        sheet.alpha_composite(img, ((i % cols) * cell_w + (cell_w - img.width) // 2, (i // cols) * cell_h + cell_h - img.height - 4))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(folder / 'preview_venue.png')

    gc, gr = 14, 11
    W, Hh = (gc + gr) * 28 + 40, (gc + gr) * 14 + 190
    ox, oy = gr * 28 + 20, 150
    scene = Image.new('RGBA', (W, Hh), (60, 64, 72, 255))
    center = lambda c, r: (ox + (c - r) * 28, oy + (c + r) * 14)
    pool = lambda c, r: 3 <= c <= 8 and 3 <= r <= 6
    for r in range(gr):
        for c in range(gc):
            ab = 'a' if (c + r) % 2 == 0 else 'b'
            if pool(c, r):
                t = assets[f'water_{ab}']
            elif c >= 10:
                t = base[f'floor_{ab}']
            elif r >= 8:
                t = multi[f'grass_{ab}']
            else:
                t = multi[f'deck_{ab}']
            x, y = center(c, r)
            scene.alpha_composite(t, (x - 28, y - 14))
    items = [('pool_ladder', 2, 4), ('diving_board', 3, 7), ('garden_tree', 1, 9), ('flower_bed', 4, 9), ('fountain', 7, 9),
             ('flower_bed', 5, 9), ('dj_booth', 0, 1), ('bar_counter', 5, 1), ('balloons', 8, 1), ('party_table', 9, 3),
             ('party_table', 9, 6), ('umbrella_table', 0, 6)]
    for c in range(10, 14):
        items.append(('stage', c, 2))
        items.append(('stage', c, 3))
    items += [('stage_screen', 10, 1), ('stage_screen', 11, 1), ('podium', 12, 4), ('speaker_stack', 10, 5),
              ('speaker_stack', 13, 5), ('chair_blue', 11, 7), ('chair_red', 12, 7)]
    extra = {'chair_blue': chair(G_BLUE), 'chair_red': chair(G_RED)}
    for kind, c, r in sorted(items, key=lambda t: (t[1] + t[2], t[0] != 'stage')):
        img = assets.get(kind) or multi.get(kind) or extra[kind]
        x, y = center(c, r)
        scene.alpha_composite(img, (x - img.width // 2, y + 14 - img.height))
    bx, by = center(10, 0)
    scene.alpha_composite(assets['wall_banner_a'], (bx - 26, by - 90))
    scene.resize((W * 2, Hh * 2), Image.NEAREST).save(folder / 'preview_venue_scene.png')

    n = 8
    t = Image.new('RGBA', (n * 56 + 56, n * 28 + 56), (60, 64, 72, 255))
    for r in range(n):
        for c in range(n):
            ab = 'a' if (c + r) % 2 == 0 else 'b'
            src = assets[f'water_{ab}'] if c < 4 else multi[f'deck_{ab}']
            t.alpha_composite(src, (n * 28 + (c - r) * 28, 14 + (c + r) * 14))
    t.resize((t.width * 3, t.height * 3), Image.NEAREST).save(folder / 'preview_venue_checker.png')


def build(preview=None):
    OUT.mkdir(parents=True, exist_ok=True)

    walls = {
        'wall_window_a': shear(wall_window(), 'A'), 'wall_window_b': shear(wall_window(), 'B'),
        'wall_board_a': shear(wall_board(), 'A'), 'wall_cork_b': shear(wall_cork(), 'B'),
        'wall_poster_a1': shear(wall_poster('chart'), 'A'), 'wall_poster_a2': shear(wall_poster('sun'), 'A'),
        'wall_poster_b': shear(wall_poster('sun'), 'B'), 'wall_logo_b': shear(wall_logo(), 'B'),
        'wall_dartboard_b': shear(wall_dartboard(), 'B'), 'wall_door_b': shear(wall_door(), 'B'),
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
        'machine_starbucks': machine_starbucks(), 'machine_zus': machine_zus(),
        'icecream': machine_icecream(), 'chiller_redbull': chiller_redbull(), 'counter_parcels': counter_parcels(),
        'floor_a': floor_tile((238, 224, 196, 255), 1), 'floor_b': floor_tile((226, 208, 174, 255), 2),
    }
    for name, img in assets.items():
        img.save(OUT / f'{name}.png')

    multi = multifloor_assets()
    for name, img in multi.items():
        img.save(OUT / f'{name}.png')

    venue = venue_assets()
    for name, img in venue.items():
        img.save(OUT / f'{name}.png')

    print(f'{len(assets) + len(walls) + len(staff) + len(multi) + len(venue)} fail ditulis ke {OUT}')

    if preview:
        make_preview(Path(preview), {**assets, 'wall_dartboard_b': walls['wall_dartboard_b'], 'wall_door_b': walls['wall_door_b']})
        make_multifloor_preview(Path(preview), multi, assets)
        make_venue_preview(Path(preview), venue, assets, multi)


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

    vendor_skins = [((242, 207, 174), (42, 34, 25)), ((141, 85, 36), (30, 24, 20)), ((217, 165, 119), (74, 48, 28)),
                    ((245, 208, 176), (24, 20, 18))]

    def style_strip(style, rows=combos):
        if style in VENDOR_STYLES or style in STYLE_TINT:
            rows = [({**VENDOR_TINT, **STYLE_TINT}[style], sk, hr) for sk, hr in vendor_skins]
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
