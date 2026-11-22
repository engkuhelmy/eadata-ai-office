import Phaser from 'phaser';
import {
    AVATARS, GRID, TILE, ORIGIN, DEPARTMENTS, DEPT_BUBBLE, DECOR, FLOORS, STAIRS, ZONES, WALL_DECOR, FLOOR_FX,
    VENDOR_COLORS, STYLE_SHIRT, VISITOR_STYLES, allSeats, blockedTiles, capacityFor, departmentsOn, floorOf,
    queueFor, seatsFor, spotFor, standsFor,
} from './layout';
import { findPath } from './pathfinding';

const WALK_SPEED = 110; // px per saat
const EXIT_DELAY_MS = 10000; // staff hilang 10s lepas sampai pintu
const VISITOR_EXIT_DELAY_MS = 1500; // pelawat (rider/kurier) hilang cepat selepas sampai pintu
const WALL_H = 130;
// Kerusi (dan staff yang duduk) dirapatkan ke meja: 40% ke arah tile meja (c, r-1)
const SEAT_SHIFT = { x: 11, y: -6 };
const GOOGLE_COLORS = ['blue', 'red', 'yellow', 'green'];
const FONT = 'system-ui, sans-serif';

// Bangunan bertingkat: setiap aras dilukis FLOOR_DY px di atas aras bawahnya (L1 paling bawah).
// Dengan 640, papak aras atas hanya menindih ~40px bahagian atas dinding belakang aras bawah.
const FLOOR_DY = 640;
const SLAB_H = 18; // tebal papak lantai
const CLIMB_MS = 1200; // naik/turun satu aras
const VIEW_MS = 800; // tween kamera antara paparan
const FIRST_FLOOR = FLOORS[0]?.id ?? 1;
const TOP_FLOOR = FLOORS[FLOORS.length - 1]?.id ?? 1;

// Tekstur sprite staff ikut gaya watak: 'default' guna nama lama staff_{layer}
const texKey = (style, layer) => `staff_${style}_${layer}`;
const texFile = (style, layer) => (style === 'default' ? `staff_${layer}` : `staff_${style}_${layer}`);
const STYLE_HAIR = {
    default: [0x2a2219, 0x6d4c2a, 0x1f2937, 0xa16207, 0x3f3f46, 0x92400e],
    woman: [0x2a2219, 0x4a2c1a, 0x6d4c2a, 0x1f2937, 0x7c2d12],
    hiphop: [0x1a1a1a, 0x2a2219, 0x3f3f46],
    genz: [0xff6fae, 0x6ee7b7, 0xa78bfa, 0x60a5fa, 0xfbbf24],
    recep: [0x3b2417, 0x2a1a10, 0x4a2c1a],
    grab: [0x1a1a1a, 0x2a2219, 0x15151a],
    shopee: [0x1a1a1a, 0x2a2219, 0x15151a],
    jnt: [0x1a1a1a, 0x2a2219, 0x15151a],
    dhl: [0x1a1a1a, 0x2a2219, 0x15151a],
    exec: [0x1f1a16, 0x2a2219, 0x3f3f46, 0x6b6b6b],
    exec_w: [0x2a2219, 0x4a2c1a, 0x1f2937, 0x6d4c2a],
};
const GOOGLE_HEX = [0x4285f4, 0xea4335, 0xfbbc05, 0x34a853];

const C = {
    wall: 0xf6f7f9,
    wallTrim: 0xdadce0,
    frame: 0x7a4f2e,
    skins: [0xf2cfae, 0xd9a577, 0x8d5524, 0xf5d0b0],
    slabTop: 0xe9e4da,
    slabLeft: 0xb9b3a8,
    slabRight: 0x8f897f,
};

// Warna kotak ganti bila sprite tiada (fail belum dijana / gagal dimuat)
const KIND = {
    desk: { h: 14, top: 0xb98b5b, left: 0x8a6239, right: 0x6e4d2b },
    table: { h: 10, top: 0x9c7a4f, left: 0x7a5c37, right: 0x654a2c },
    sofa: { h: 16, top: 0xc0462c, left: 0x8e3320, right: 0x6e2616 },
    cooler: { h: 30, top: 0xe0f2fe, left: 0x93c5fd, right: 0x60a5fa },
    machine: { h: 24, top: 0x6d4c41, left: 0x4e342e, right: 0x3e2723 },
    bell: { h: 16, top: 0xf5d37a, left: 0xc9a845, right: 0xb0903a },
    reception: { h: 16, top: 0x9a6a3c, left: 0x73492a, right: 0x5e3a20 },
    server: { h: 44, top: 0x37474f, left: 0x263238, right: 0x1c262b },
    shelf: { h: 42, top: 0x6d4c2a, left: 0x5a3a20, right: 0x4a2e18 },
    pong: { h: 6, top: 0x2e7d32, left: 0x1b5e20, right: 0x145a1a },
    foos: { h: 10, top: 0x1565c0, left: 0x0d47a1, right: 0x0b3d91 },
    stairs: { h: 34, top: 0xcfc8bb, left: 0x9a9284, right: 0x7d766a },
    stair_hut: { h: 60, top: 0xd6d3cc, left: 0xa8a49b, right: 0x8b877f },
    glass: { h: 40, top: 0xcfe8f7, left: 0x9cc9e6, right: 0x7fb3d6 },
    railing: { h: 18, top: 0xcfe8f7, left: 0x9cc9e6, right: 0x7fb3d6 },
    beanbag: { h: 10, top: 0x4285f4, left: 0x2f6bd0, right: 0x2557ad },
    fallback: { h: 12, top: 0xb0a898, left: 0x8a8274, right: 0x6f685c },
};
const kindStyle = (key) => KIND[key] ?? KIND[String(key).split('_')[0]] ?? KIND.fallback;

const SCREEN_BG = { ok: 0x14321f, approval: 0x3d2a08, error: 0x3d0f0f };
const CODE_FG = { ok: 0x6ee7a0, approval: 0xfbbf24, error: 0xff7070 };

const STATUS_TEXT = {
    active: 'Kerja...',
    idle: '',
    error: 'Ada error!',
    needs_approval: 'Perlu approval',
    rate_limited: 'Rehat dulu',
    ended: '',
};

// Sprite yang sedia ada + sprite baharu dalam spec (fail yang tiada tidak memecahkan apa-apa)
const IMAGE_NAMES = [
    'wall_window_a', 'wall_window_b', 'wall_board_a', 'wall_cork_b', 'wall_poster_a1', 'wall_poster_a2', 'wall_poster_b',
    'wall_door_b', 'wall_dartboard_b', 'wall_logo_b', 'partition_a', 'partition_b', 'partition_a_logo', 'partition_b_logo',
    'floor_a', 'floor_b', 'desk', 'plant', 'shelf', 'cooler', 'machine', 'server', 'pong', 'foos', 'table', 'reception', 'bell',
    'snooker', 'fridge', 'wc', 'sink', 'boardtable',
    'machine_starbucks', 'machine_zus', 'icecream', 'chiller_redbull', 'counter_parcels',
    ...GOOGLE_COLORS.map((c) => `chair_${c}`), ...GOOGLE_COLORS.map((c) => `sofa_${c}`),
    'stairs', 'stair_hut', 'training_desk', 'projector_screen', 'whiteboard', 'coffee_table', 'exec_desk', 'glass_a', 'glass_b',
    'arcade', 'tv_console', 'beanbag_blue', 'beanbag_red', 'beanbag_yellow', 'beanbag_green', 'umbrella_table', 'lounger', 'bbq',
    'planter', 'outdoor_desk', 'ac_unit', 'pantry_counter', 'railing_a', 'railing_b',
    'deck_a', 'deck_b', 'grass_a', 'grass_b', 'carpet_a', 'carpet_b',
];

// Nama sprite yang dirujuk oleh pelan lantai (supaya kind baharu turut dimuat)
function layoutImageNames() {
    const names = new Set();
    for (const d of Object.values(DEPARTMENTS)) for (const cell of d.cells ?? []) names.add(cell.kind);
    for (const item of DECOR) if (item.kind !== 'block') names.add(item.kind); // 'block' = penghalang tak kelihatan (cth. air kolam)
    for (const w of WALL_DECOR) names.add(w.key);
    for (const z of ZONES) {
        if (z.tile) {
            names.add(`${z.tile}_a`);
            names.add(`${z.tile}_b`);
        }
    }

    return [...names].filter((n) => typeof n === 'string' && /^[a-z0-9_]+$/i.test(n));
}

// ---------- Geometri ----------

// Grid corner (c, r) → skrin (isometric), unjuran setempat (aras L1)
export function corner(c, r) {
    return {
        x: ORIGIN.x + ((c - r) * TILE.w) / 2,
        y: ORIGIN.y + ((c + r) * TILE.h) / 2,
    };
}

// Titik tengah tile (c, r) → skrin (aras L1)
export function tileCenter(c, r) {
    return corner(c + 0.5, r + 0.5);
}

const floorIndex = (id) => Math.max(0, FLOORS.findIndex((f) => f.id === id));
const floorDy = (id) => -floorIndex(id) * FLOOR_DY;

// Sama seperti corner/tileCenter tetapi pada ofset dunia aras f
function cornerF(f, c, r) {
    const p = corner(c, r);
    return { x: p.x, y: p.y + floorDy(f) };
}

function tileCenterF(f, c, r) {
    return cornerF(f, c + 0.5, r + 0.5);
}

// Titik pada dinding: wall 'A' sepanjang c (r=1), wall 'B' sepanjang r (c=1). v = ketinggian.
function wallPtF(f, wall, u, v) {
    const p = wall === 'A' ? cornerF(f, u, 1) : cornerF(f, 1, u);

    return { x: p.x, y: p.y - v };
}

// Tag pendek aras untuk UI: 'L1', 'L2', 'L3', 'Rooftop'
export function floorTag(f) {
    if (!f) return '';
    return /^level/i.test(f.label ?? '') ? f.key : f.label;
}

function hashOf(id) {
    return String(id).split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
}

function offsetFor(id) {
    const n = hashOf(id);

    return { x: ((n % 5) - 2) * 7, y: ((n % 3) - 1) * 3 };
}

function polygon(g, points, color, alpha = 1) {
    g.fillStyle(color, alpha);
    g.beginPath();
    g.moveTo(points[0].x, points[0].y);
    for (const p of points.slice(1)) {
        g.lineTo(p.x, p.y);
    }
    g.closePath();
    g.fillPath();
}

function outline(g, points, color, width = 1, alpha = 1, close = true) {
    g.lineStyle(width, color, alpha);
    g.beginPath();
    g.moveTo(points[0].x, points[0].y);
    for (const p of points.slice(1)) {
        g.lineTo(p.x, p.y);
    }
    if (close) g.closePath();
    g.strokePath();
}

// Kotak isometric berpusat di (x, y) setinggi h
function drawBoxAt(g, x, y, h, st) {
    const hw = TILE.w / 2;
    const hh = TILE.h / 2;

    polygon(g, [{ x: x - hw, y: y - h }, { x, y: y - h - hh }, { x: x + hw, y: y - h }, { x, y: y - h + hh }], st.top);
    polygon(g, [{ x: x - hw, y: y - h }, { x, y: y - h + hh }, { x, y: y + hh }, { x: x - hw, y }], st.left);
    polygon(g, [{ x: x + hw, y: y - h }, { x, y: y - h + hh }, { x, y: y + hh }, { x: x + hw, y }], st.right);
}

function tilePolyF(g, f, c, r, color, alpha) {
    const { x, y } = tileCenterF(f, c, r);
    const hw = TILE.w / 2;
    const hh = TILE.h / 2;

    polygon(g, [{ x, y: y - hh }, { x: x + hw, y }, { x, y: y + hh }, { x: x - hw, y }], color, alpha);
}

export default class OfficeScene extends Phaser.Scene {
    constructor() {
        super('office');
        this.staff = new Map();
        this.seatOwner = new Map(); // "floor:c,r" -> staff id
        this.screens = [];
        this.deptState = {};
        this.pending = null;
        this.ready = false;
        this.screenTimer = 0;
        this.view = 'building'; // 'building' atau id aras
        this.textMode = false; // nama + bubble dipapar (paparan aras sahaja)
        this.initialDone = false;
        this.selectedId = null;
        this.floorCounts = {};
        this.onSelect = () => {};
        this.onViewChange = () => {};
    }

    preload() {
        // Lebih 32 fail: batch kedua loader Phaser tersekat dalam pane tersembunyi, jadi muat semua sekali gus.
        this.load.maxParallelDownloads = 256;

        // Sprite sheet staff: gaya x 4 lapisan (fixed, skin, hair, shirt), 16 frame 32x48.
        // Frame: 0-1 idle, 2-5 jalan, 6-7 duduk depan, 8-9 duduk belakang, 10-11 main, 12-13 dart, 14-15 minum.
        for (const style of AVATARS) {
            for (const layer of ['fixed', 'skin', 'hair', 'shirt']) {
                this.load.spritesheet(texKey(style, layer), `/assets/office/${texFile(style, layer)}.png`, { frameWidth: 32, frameHeight: 48 });
            }
        }
        for (const name of new Set([...IMAGE_NAMES, ...layoutImageNames()])) {
            this.load.image(name, `/assets/office/${name}.png`);
        }
    }

    // ---------- Pembantu aras ----------

    layerOf(f) {
        return this.layers.get(f) ?? this.layers.get(FIRST_FLOOR);
    }

    // Masukkan objek ke lapisan aras f (jalur depth berasingan setiap aras)
    put(f, obj) {
        this.layerOf(f).add(obj);
        return obj;
    }

    blockedFor(f) {
        if (!this.blockedCache.has(f)) this.blockedCache.set(f, blockedTiles(f));
        return this.blockedCache.get(f);
    }

    slotKey(f, cell) {
        return `${f}:${cell.c},${cell.r}`;
    }

    // Letak sprite furniture pada tile (c, r) aras f. Anchor: bucu bawah tile (tengah + 14px).
    // Sprite tiada: kotak isometric ganti.
    placeSprite(f, key, c, r, depth = c + r, dy = 14) {
        const { x, y } = tileCenterF(f, c, r);
        if (!this.textures.exists(key)) {
            const g = this.put(f, this.add.graphics().setDepth(depth));
            const st = kindStyle(key);
            drawBoxAt(g, x, y, st.h, st);
            return g;
        }

        return this.put(f, this.add.image(x, y + dy, key).setOrigin(0.5, 1).setDepth(depth));
    }

    create() {
        this.layers = new Map();
        FLOORS.forEach((f, i) => this.layers.set(f.id, this.add.layer().setDepth(10 + i)));
        this.blockedCache = new Map();
        this.deptLabels = [];
        this.fxPuffs = [];

        this.drawSky();
        const hasDoor = WALL_DECOR.some((w) => w.key === 'wall_door_b');
        for (const f of FLOORS) {
            this.drawFloorBase(f);
            if (f.walls) this.drawWalls(f, hasDoor);
            this.drawStatic(f);
            this.drawLabels(f);
            this.addAmbient(f);
        }
        this.startPuffs();
        this.drawBanners();

        // Bungkusan di kaunter reception (tersembunyi sampai pelawat serah barang)
        this.parcelWanted = false;
        this.recepAway = false;
        this.handoverIds = new Set();
        const counters = (DEPARTMENTS.door?.cells ?? []).filter((cell) => cell.kind === 'reception');
        const counter = counters[counters.length - 1] ?? { c: 4, r: 13 };
        this.parcels = this.textures.exists('counter_parcels')
            ? this.placeSprite(floorOf('door'), 'counter_parcels', counter.c, counter.r, counter.c + counter.r + 0.1).setAlpha(0)
            : null;

        // Cahaya siang neutral-hangat + malam: segi empat besar dalam ruang dunia (kamera zoom tak memotongnya)
        const b = this.buildingBounds();
        const cx = (b.x0 + b.x1) / 2;
        const cy = (b.y0 + b.y1) / 2;
        this.lighting = this.add.rectangle(cx, cy, 40000, 40000, 0xfff1d0, 0.04).setDepth(3000);
        // Siang dan malam ikut jam setempat (?hour=22 untuk uji). Dikemas kini setiap minit.
        this.night = this.add.rectangle(cx, cy, 40000, 40000, 0x0b1d4a, 0).setDepth(3001);
        this.applyDayNight();
        this.time.addEvent({ delay: 60000, loop: true, callback: () => this.applyDayNight() });

        // Paparan bangunan: klik satu aras untuk zoom masuk
        this.input.on('pointerdown', (pointer, over) => {
            if (this.view !== 'building' || over.length) return;
            const p = this.cameras.main.getWorldPoint(pointer.x, pointer.y);
            const f = this.floorAt(p.x, p.y);
            if (f !== null) this.setView(f);
        });

        this.ready = true;
        this.setView(this.view, { instant: true });

        if (this.pending) {
            const { agents, opts } = this.pending;
            this.pending = null;
            this.render(agents, opts);
        }
    }

    // Kelegapan malam: 0 siang (7-17), naik perlahan waktu senja/subuh, paling gelap 21-4.
    applyDayNight() {
        let hour = new Date().getHours() + new Date().getMinutes() / 60;
        try {
            const forced = new URLSearchParams(window.location.search).get('hour');
            if (forced !== null && forced !== '') hour = Number(forced);
        } catch {
            // abaikan
        }

        const curve = [[0, 0.3], [4, 0.3], [6.5, 0.08], [8, 0], [17, 0], [19, 0.1], [21, 0.28], [24, 0.3]];
        let alpha = 0;
        for (let i = 1; i < curve.length; i++) {
            if (hour <= curve[i][0]) {
                const [h0, a0] = curve[i - 1];
                const [h1, a1] = curve[i];
                alpha = a0 + ((a1 - a0) * (hour - h0)) / (h1 - h0);
                break;
            }
        }
        this.night.setAlpha(alpha);
    }

    // ---------- Bangunan ----------

    // Kotak sempadan seluruh bangunan (semua aras), dalam koordinat dunia
    buildingBounds() {
        return {
            x0: cornerF(FIRST_FLOOR, 1, GRID.rows).x,
            x1: cornerF(FIRST_FLOOR, GRID.cols, 1).x,
            y0: cornerF(TOP_FLOOR, 1, 1).y - 170,
            y1: cornerF(FIRST_FLOOR, GRID.cols, GRID.rows).y + SLAB_H,
        };
    }

    // Langit lembut di belakang bangunan + tanah di bawah L1 (nampak dalam paparan bangunan sahaja)
    drawSky() {
        const b = this.buildingBounds();
        const g = this.add.graphics().setDepth(0);
        const horizon = cornerF(FIRST_FLOOR, 1, 1).y;
        const x0 = b.x0 - 8000;
        const w = b.x1 - b.x0 + 16000;
        const top = 0x6aa9dc;
        const haze = 0xdcefff;

        g.fillStyle(top, 1).fillRect(x0, b.y0 - 8000, w, 8000);
        g.fillGradientStyle(top, top, haze, haze, 1).fillRect(x0, b.y0, w, horizon - b.y0);
        g.fillGradientStyle(0xb7cfa4, 0xb7cfa4, 0x88a877, 0x88a877, 1).fillRect(x0, horizon, w, b.y1 + 260 - horizon);
        g.fillStyle(0x88a877, 1).fillRect(x0, b.y1 + 260, w, 8000);

        // Bayang bangunan atas tanah
        const sh = [cornerF(FIRST_FLOOR, 0, 0), cornerF(FIRST_FLOOR, GRID.cols + 1, 0), cornerF(FIRST_FLOOR, GRID.cols + 1, GRID.rows + 1), cornerF(FIRST_FLOOR, 0, GRID.rows + 1)]
            .map((p) => ({ x: p.x, y: p.y + SLAB_H + 6 }));
        polygon(g, sh, 0x000000, 0.16);

        this.sky = g;
    }

    // Papak lantai (dengan ketebalan), jubin lantai, zon (dek/rumput/karpet) dan tint permaidani
    drawFloorBase(f) {
        const g = this.put(f.id, this.add.graphics().setDepth(-1100));
        const L = cornerF(f.id, 1, GRID.rows);
        const F = cornerF(f.id, GRID.cols, GRID.rows);
        const R = cornerF(f.id, GRID.cols, 1);
        const down = (p) => ({ x: p.x, y: p.y + SLAB_H });

        polygon(g, [L, F, down(F), down(L)], C.slabLeft);
        polygon(g, [F, R, down(R), down(F)], C.slabRight);
        outline(g, [down(L), down(F), down(R)], 0x6f695f, 1, 0.8, false);
        // Jalur warna Google pada tepi papak
        for (let u = 1, i = 0; u < GRID.cols; u += 1.5, i++) {
            const a = cornerF(f.id, u, GRID.rows);
            const z = cornerF(f.id, Math.min(u + 1.5, GRID.cols), GRID.rows);
            polygon(g, [a, z, { x: z.x, y: z.y + 3 }, { x: a.x, y: a.y + 3 }], GOOGLE_HEX[i % 4], 0.9);
        }

        // Jubin: zon dengan `tile` gantikan kayu (entri kemudian menang)
        const zoneTile = new Map();
        const zones = ZONES.filter((z) => (z.floor ?? 1) === f.id);
        for (const z of zones) {
            if (!z.tile) continue;
            for (let r = z.r0; r <= z.r1; r++) for (let c = z.c0; c <= z.c1; c++) zoneTile.set(`${c},${r}`, z.tile);
        }
        for (let r = 1; r < GRID.rows; r++) {
            for (let c = 1; c < GRID.cols; c++) {
                const { x, y } = tileCenterF(f.id, c, r);
                const ab = (c + r) % 2 === 0 ? 'a' : 'b';
                const tile = zoneTile.get(`${c},${r}`);
                let key = tile ? `${tile}_${ab}` : `floor_${ab}`;
                if (!this.textures.exists(key)) key = `floor_${ab}`;
                this.put(f.id, this.add.image(x, y, key).setDepth(-1001));
            }
        }

        // Tint permaidani
        const tint = this.put(f.id, this.add.graphics().setDepth(-1000));
        for (const z of zones) {
            if (z.color === undefined || z.color === null) continue;
            for (let r = z.r0; r <= z.r1; r++) {
                for (let c = z.c0; c <= z.c1; c++) tilePolyF(tint, f.id, c, r, z.color, z.alpha ?? 0.15);
            }
        }
        // Air kolam: kilauan lembut berdenyut (jubin 'water', fasa ikut kedudukan supaya nampak beriak)
        for (const [key, tile] of zoneTile) {
            if (tile !== 'water') continue;
            const [c, r] = key.split(',').map(Number);
            const shimmer = this.put(f.id, this.add.graphics().setDepth(-999));
            tilePolyF(shimmer, f.id, c, r, 0xffffff, 0.22);
            shimmer.setAlpha(0.2);
            this.tweens.add({
                targets: shimmer,
                alpha: { from: 0.05, to: 0.7 },
                duration: 1100 + ((c * 7 + r * 13) % 5) * 180,
                delay: ((c + r) % 6) * 160,
                yoyo: true,
                repeat: -1,
                ease: 'Sine.easeInOut',
            });
        }
        // Tepi hadapan lantai
        outline(tint, [L, F, R], C.slabTop, 2, 0.9, false);
    }

    drawWalls(f, hasDoor) {
        const g = this.put(f.id, this.add.graphics().setDepth(-900));
        const wp = (wall, u, v) => wallPtF(f.id, wall, u, v);
        const quad = (wall, u0, u1, v0, v1, color) => polygon(g, [wp(wall, u0, v0), wp(wall, u1, v0), wp(wall, u1, v1), wp(wall, u0, v1)], color);

        // Dinding belakang
        quad('A', 1, GRID.cols, 0, WALL_H, C.wall);
        quad('B', 1, GRID.rows, 0, WALL_H, C.wall);
        quad('A', 1, GRID.cols, 0, 6, C.wallTrim);
        quad('B', 1, GRID.rows, 0, 6, C.wallTrim);
        // Kemasan atas dinding (nampak sebagai tebal dinding dalam paparan bangunan)
        outline(g, [wp('B', GRID.rows, WALL_H), wp('B', 1, WALL_H), wp('A', GRID.cols, WALL_H)], 0xc4c7cc, 3, 1, false);

        // Panel bawah dinding (wainscot)
        quad('A', 1, GRID.cols, 6, 30, 0xe8eaed);
        quad('B', 1, GRID.rows, 6, 30, 0xe8eaed);
        outline(g, [wp('A', 1, 30), wp('A', GRID.cols, 30)], 0xbdc1c6, 2);
        outline(g, [wp('B', 1, 30), wp('B', GRID.rows, 30)], 0xbdc1c6, 2);
        // Jalur empat warna Google di kaki dinding
        for (let u = 1, i = 0; u < GRID.cols; u += 1.5, i++) quad('A', u, Math.min(u + 1.5, GRID.cols), 6, 13, GOOGLE_HEX[i % 4]);
        for (let u = 1, i = 2; u < GRID.rows; u += 1.5, i++) quad('B', u, Math.min(u + 1.5, GRID.rows), 6, 13, GOOGLE_HEX[i % 4]);

        // Hiasan dinding aras ini (sprite pixel art yang di-shear ikut dinding)
        const items = WALL_DECOR.filter((w) => (w.floor ?? 1) === f.id);
        const light = this.put(f.id, this.add.graphics().setDepth(-950).setBlendMode(Phaser.BlendModes.ADD));
        const covered = { A: [], B: [] };
        for (const item of items) {
            const w = this.textures.exists(item.key) ? this.textures.get(item.key).getSourceImage().width : 56;
            covered[item.wall]?.push([item.u, item.u + w / 28]);

            if (item.key === 'wall_door_b') {
                this.drawEntrance(f, item);
                continue;
            }
            this.wallSprite(f, item.key, item.wall, item.u, item.vTop);

            if (item.key.includes('window')) {
                const u = item.u;
                const pts = item.wall === 'A'
                    ? [cornerF(f.id, u, 1), cornerF(f.id, u + 1.6, 1), cornerF(f.id, u + 0.1, 4.5), cornerF(f.id, u - 1.5, 4.5)]
                    : [cornerF(f.id, 1, u), cornerF(f.id, 1, u + 1.6), cornerF(f.id, 4.5, u + 0.1), cornerF(f.id, 4.5, u - 1.5)];
                polygon(light, pts, 0xfff6d6, 0.12);
            }
        }
        // Pelan lantai belum ada pintu: lukis pintu lama ikut spot 'door'
        if (!hasDoor && f.id === floorOf('door')) this.drawEntrance(f, null);

        // Jam dinding di ruang kosong pertama dinding A
        const clockU = [16.5, 14, 22, 10, 4].find((u) => !covered.A.some(([a, z]) => u > a - 0.5 && u < z + 0.5));
        if (clockU !== undefined) {
            const clock = wp('A', clockU, 100);
            g.fillStyle(0xfffdf5, 1).fillCircle(clock.x, clock.y, 9);
            g.lineStyle(2, C.frame, 1).strokeCircle(clock.x, clock.y, 9);
            g.lineStyle(1.5, 0x2a2219, 1);
            g.lineBetween(clock.x, clock.y, clock.x, clock.y - 6);
            g.lineBetween(clock.x, clock.y, clock.x + 4, clock.y + 1);
        }
    }

    // Sprite dinding: A (origin kiri-atas) di u0, B (origin kanan-atas) di u0, ketinggian atas = vTop
    wallSprite(f, key, wall, u0, vTop) {
        if (!this.textures.exists(key)) return null;
        const p = wallPtF(f.id, wall, u0, vTop);

        return this.put(f.id, this.add.image(p.x, p.y, key).setOrigin(wall === 'A' ? 0 : 1, 0).setDepth(-890));
    }

    // Pintu masuk di dinding B + butang loceng di sebelahnya. item = entri WALL_DECOR (atau null: kira dari spot 'door').
    // Sprite di-shear: tinggi tekstur = tinggi asal + lebar/2, jadi tinggi asal (vTop) = H - floor(W/2).
    drawEntrance(f, item) {
        const doorSpot = spotFor('door');
        let bellU = (item?.u ?? doorSpot.r) + 2;

        if (this.textures.exists('wall_door_b')) {
            const src = this.textures.get('wall_door_b').getSourceImage();
            const w = src.width;
            const u0 = item ? item.u : doorSpot.r + 0.5 - w / 56;
            const vTop = item?.vTop ?? src.height - Math.floor(w / 2);
            this.wallSprite(f, 'wall_door_b', 'B', u0, vTop);
            bellU = u0 + w / 28 + 0.4;
        }

        // Pelat loceng pada dinding + butang merah
        const g = this.put(f.id, this.add.graphics().setDepth(-889));
        const wp = (u, v) => wallPtF(f.id, 'B', u, v);
        polygon(g, [wp(bellU - 0.13, 42), wp(bellU + 0.13, 42), wp(bellU + 0.13, 62), wp(bellU - 0.13, 62)], 0xdadce0);
        outline(g, [wp(bellU - 0.13, 42), wp(bellU + 0.13, 42), wp(bellU + 0.13, 62), wp(bellU - 0.13, 62)], 0x8a8f98, 1);

        const p = wp(bellU, 52);
        this.bellFloor = f.id;
        this.bellPos = { x: p.x, y: p.y };
        this.bellGlow = this.put(f.id, this.add.circle(p.x, p.y, 7, 0xfbbc05, 0).setBlendMode(Phaser.BlendModes.ADD).setDepth(-880));
        this.bellBtn = this.put(f.id, this.add.circle(p.x, p.y, 3.5, 0xea4335).setStrokeStyle(1, 0x3a2414).setDepth(-879));
    }

    // Loceng pintu: butang berdenyut dan bergetar, gelombang bunyi, teks "Ding dong!", bunyi chime (kalau dibenarkan browser)
    ringDoorbell() {
        if (!this.bellBtn || !this.bellPos) return;
        const now = this.time.now;
        if (now - (this.lastRing ?? -1e9) < 1500) return;
        this.lastRing = now;

        const f = this.bellFloor;
        const { x, y } = this.bellPos;
        this.tweens.add({ targets: this.bellBtn, scale: { from: 0.7, to: 1.3 }, duration: 110, yoyo: true, repeat: 2 });
        this.tweens.add({ targets: this.bellBtn, x: x + 1.5, duration: 40, yoyo: true, repeat: 7, onComplete: () => this.bellBtn.setX(x) });
        this.bellGlow.setAlpha(0.8).setScale(1);
        this.tweens.add({ targets: this.bellGlow, alpha: 0, scale: 2.4, duration: 900 });

        for (let i = 0; i < 3; i++) {
            this.time.delayedCall(i * 220, () => {
                const ring = this.put(f, this.add.circle(x, y, 4, 0xffffff, 0).setStrokeStyle(2, 0xfbbc05, 0.9).setDepth(-878));
                this.tweens.add({ targets: ring, scale: 5, alpha: 0, duration: 800, onComplete: () => ring.destroy() });
            });
        }

        const text = this.put(f, this.add
            .text(x, y - 30, 'Ding dong!', {
                fontFamily: FONT,
                fontSize: '12px',
                fontStyle: 'bold',
                color: '#2a2219',
                backgroundColor: '#fff3c4',
                padding: { x: 6, y: 3 },
            })
            .setOrigin(0.5, 1)
            .setDepth(60000));
        this.tweens.add({ targets: text, y: y - 36, duration: 300, ease: 'Back.easeOut' });
        this.tweens.add({ targets: text, alpha: 0, delay: 2500, duration: 500, onComplete: () => text.destroy() });

        this.chime();
    }

    // Dua nota lembut. Senyap kalau audio disekat browser (tiada interaksi pengguna lagi). Tak pernah throw.
    chime() {
        try {
            if (!navigator.userActivation?.hasBeenActive) return;
            const AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return;
            this.audio ??= new AC();
            const ctx = this.audio;
            if (ctx.state === 'suspended') ctx.resume().catch(() => {});
            if (ctx.state !== 'running') return;

            [[880, 0], [659, 0.24]].forEach(([freq, at]) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                const t = ctx.currentTime + at;
                osc.type = 'sine';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.0001, t);
                gain.gain.exponentialRampToValueAtTime(0.05, t + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.7);
                osc.connect(gain).connect(ctx.destination);
                osc.start(t);
                osc.stop(t + 0.75);
            });
        } catch {
            // abaikan: bunyi hanya hiasan
        }
    }

    // Resepsionis sampai ke satu department: sampul surat kecil naik dan lenyap (hantar arahan)
    sendNote(s) {
        const env = this.put(s.floor, this.add.graphics().setDepth(60000));
        env.fillStyle(0xffffff, 1).fillRect(-7, -5, 14, 10);
        env.lineStyle(1, 0x3a2414, 1).strokeRect(-7, -5, 14, 10);
        env.lineBetween(-7, -5, 0, 1);
        env.lineBetween(7, -5, 0, 1);
        env.fillStyle(0x4285f4, 1).fillCircle(5, 4, 2);
        env.setPosition(s.pos.x + 22, s.pos.y - 32);
        this.tweens.add({ targets: env, scale: { from: 0.5, to: 1.15 }, duration: 220, ease: 'Back.easeOut' });
        this.tweens.add({ targets: env, y: s.pos.y - 62, x: s.pos.x + 26, alpha: 0, delay: 350, duration: 1300, onComplete: () => env.destroy() });
    }

    // Bungkusan atas kaunter: muncul bila pelawat mula serah barang, hilang bila resepsionis keluar mengedar.
    // Alpha dilicinkan (lerp) supaya tak berkelip.
    updateParcels(delta) {
        if (!this.parcels) return;

        const handing = new Set();
        let recepCount = 0;
        let recepAway = false;
        for (const s of this.staff.values()) {
            if (s.activity === 'handover') handing.add(s.id);
            if (s.style === 'recep' && !s.leaving) {
                recepCount++;
                if (s.dept && s.dept !== 'frontdesk') recepAway = true;
            }
        }

        if (recepAway && !this.recepAway) this.parcelWanted = false;
        this.recepAway = recepAway;
        for (const id of handing) {
            if (!this.handoverIds.has(id)) this.parcelWanted = true;
        }
        this.handoverIds = handing;
        if (recepCount === 0 && handing.size === 0) this.parcelWanted = false;

        const target = this.parcelWanted ? 1 : 0;
        const a = this.parcels.alpha + (target - this.parcels.alpha) * Math.min(1, delta / 180);
        this.parcels.setAlpha(Math.abs(target - a) < 0.02 ? target : a);
    }

    drawLabels(f) {
        for (const key of departmentsOn(f.id)) {
            const dept = DEPARTMENTS[key];
            if (dept.hideLabel) continue;
            const cell = dept.cells?.[0];
            const { x, y } = cell ? tileCenterF(f.id, cell.c, cell.r) : tileCenterF(f.id, dept.spot.c, dept.spot.r);

            const label = this.add
                .text(x, y - 46, dept.label, {
                    fontFamily: FONT,
                    fontSize: '11px',
                    color: '#2a2219',
                    backgroundColor: '#fffdf5',
                    padding: { x: 6, y: 3 },
                })
                .setOrigin(0.5)
                .setDepth(50000);
            this.deptLabels.push(this.put(f.id, label));
        }
    }

    // Furniture statik + skrin monitor (skrin dikemaskini dalam update)
    drawStatic(f) {
        const fid = f.id;

        // Kerusi di setiap seat. Sandaran menghadap kamera dan dilukis DI DEPAN staff yang duduk
        // (depth +0.6 vs staff +0.5), jadi nampak macam duduk membelakangkan kita, menghadap meja.
        for (const seat of allSeats(fid)) {
            const color = GOOGLE_COLORS[(seat.c + seat.r) % GOOGLE_COLORS.length];
            const key = `chair_${color}`;
            if (!this.textures.exists(key)) continue;
            const { x, y } = tileCenterF(fid, seat.c, seat.r);
            this.put(fid, this.add.image(x + SEAT_SHIFT.x, y + SEAT_SHIFT.y + 3, key).setOrigin(0.5, 37 / 40).setDepth(seat.c + seat.r + 0.6));
        }

        const used = new Set();
        const place = (kind, c, r, dept) => {
            used.add(`${c},${r}`);
            if (kind === 'plant') {
                this.drawPlant(fid, c, r);
                return;
            }
            const { x, y } = tileCenterF(fid, c, r);
            this.placeSprite(fid, kind, c, r);

            if (kind === 'desk' && dept) {
                // Skrin monitor animasi (kawasan 10x7 pada sprite desk), plus lampu berdenyut
                const screen = this.put(fid, this.add.graphics().setDepth(c + r + 0.2));
                this.screens.push({ g: screen, floor: fid, x, y: y - 29, dept, seed: hashOf(`${c},${r}`) % 7 });

                const lamp = this.put(fid, this.add
                    .circle(x + 8, y - 18, 14, 0xffc46b, 0.12)
                    .setBlendMode(Phaser.BlendModes.ADD)
                    .setDepth(c + r + 0.3));
                this.tweens.add({ targets: lamp, alpha: { from: 0.05, to: 0.18 }, duration: 1400 + (c * 90) % 500, yoyo: true, repeat: -1 });
            }
            if (kind === 'server') {
                // LED berkelip pada muka kiri rak
                for (let i = 0; i < 4; i++) {
                    const led = this.put(fid, this.add.circle(x - 22 + i * 5, y - 33 + i * 2.5, 1.6, i % 2 ? 0x22c55e : 0xfbbf24).setDepth(c + r + 0.1));
                    this.tweens.add({ targets: led, alpha: { from: 0.2, to: 1 }, duration: 350 + i * 170, yoyo: true, repeat: -1 });
                }
            }
        };

        for (const key of departmentsOn(fid)) {
            for (const cell of DEPARTMENTS[key].cells ?? []) place(cell.kind, cell.c, cell.r, key);
        }
        for (const item of DECOR) {
            if ((item.floor ?? 1) !== fid || item.kind === 'block') continue;
            for (const cell of item.cells) place(item.kind, cell.c, cell.r, null);
        }

        // Tangga (sama kedudukan setiap aras): pondok tangga di rooftop
        if (!used.has(`${STAIRS.cell.c},${STAIRS.cell.r}`)) {
            this.placeSprite(fid, fid === TOP_FLOOR || !f.walls ? 'stair_hut' : 'stairs', STAIRS.cell.c, STAIRS.cell.r);
        }
    }

    drawPlant(f, c, r) {
        if (!this.textures.exists('plant')) {
            this.placeSprite(f, 'plant', c, r);
            return;
        }
        const { x, y } = tileCenterF(f, c, r);
        const plant = this.put(f, this.add.image(x, y + 8, 'plant').setOrigin(0.5, 1).setDepth(c + r));
        this.tweens.add({ targets: plant, angle: { from: -1.5, to: 1.5 }, duration: 2200, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
    }

    addAmbient(f) {
        const dy = floorDy(f.id);

        // Dust motes dalam cahaya tingkap
        if (f.walls) {
            for (let i = 0; i < 10; i++) {
                const x = 380 + Math.random() * 420;
                const y = 150 + dy + Math.random() * 200;
                const mote = this.put(f.id, this.add.circle(x, y, 1.6, 0xfff7d6, 0.6).setDepth(40000));
                this.tweens.add({
                    targets: mote,
                    x: x + (Math.random() * 40 - 20),
                    y: y - 18,
                    alpha: { from: 0.1, to: 0.8 },
                    duration: 3000 + Math.random() * 2500,
                    yoyo: true,
                    repeat: -1,
                    ease: 'Sine.easeInOut',
                });
            }
        }

        // Kesan ambien dari pelan lantai: wap kopi, gelembung water cooler, bola ping-pong
        for (const fx of FLOOR_FX) {
            if ((fx.floor ?? 1) !== f.id) continue;
            const p = tileCenterF(f.id, fx.c, fx.r);
            if (fx.kind === 'pong') {
                const ball = this.put(f.id, this.add.circle(p.x - 16, p.y - 12, 2, 0xffffff).setDepth(fx.c + fx.r + 1.7));
                this.tweens.add({ targets: ball, x: p.x + 16, duration: 520, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
                this.tweens.add({ targets: ball, y: p.y - 20, duration: 260, yoyo: true, repeat: -1, ease: 'Sine.easeOut' });
            } else if (fx.kind === 'steam') {
                this.fxPuffs.push({ floor: f.id, x: p.x - 3, y: p.y - 40, color: 0xf5f5f4, rise: 26, duration: 1600 });
            } else if (fx.kind === 'bubbles') {
                this.fxPuffs.push({ floor: f.id, x: p.x, y: p.y - 42, color: 0xbfe9ff, rise: 18, duration: 1000 });
            }
        }
    }

    startPuffs() {
        if (!this.fxPuffs.length) return;
        this.time.addEvent({
            delay: 800,
            loop: true,
            callback: () => {
                for (const fx of this.fxPuffs) {
                    if (!this.layerOf(fx.floor).visible) continue;
                    this.puff(fx.floor, fx.x, fx.y, fx.color, fx.rise, fx.duration);
                }
            },
        });
    }

    puff(f, x, y, color, rise, duration) {
        const dot = this.put(f, this.add.circle(x + (Math.random() * 6 - 3), y, 3, color, 0.7).setDepth(9000));
        this.tweens.add({
            targets: dot,
            y: y - rise,
            alpha: 0,
            scale: 2,
            duration,
            onComplete: () => dot.destroy(),
        });
    }

    // Sepanduk setiap aras di kiri bangunan (paparan bangunan): label, nama, kiraan staff. Klik untuk zoom masuk.
    drawBanners() {
        this.banners = new Map();
        this.bannerW = 0;
        for (const f of FLOORS) {
            const L = cornerF(f.id, 1, GRID.rows);
            const B = cornerF(f.id, 1, 1);
            const y = (L.y + B.y) / 2 + (f.walls ? -10 : 20);
            const x = L.x - 70;

            const line = this.add.graphics().setDepth(3100);
            line.lineStyle(4, 0xf5efe6, 0.55).lineBetween(x, y, L.x - 6, L.y - 6);
            line.fillStyle(0xf5efe6, 0.8).fillCircle(L.x - 6, L.y - 6, 7);

            const text = this.add
                .text(x, y, '', {
                    fontFamily: FONT,
                    fontSize: '40px',
                    color: '#f5efe6',
                    backgroundColor: '#2a2521',
                    align: 'right',
                    padding: { x: 26, y: 16 },
                    lineSpacing: 6,
                })
                .setOrigin(1, 0.5)
                .setDepth(3101)
                .setInteractive({ useHandCursor: true });
            text.on('pointerdown', () => {
                if (this.view === 'building') this.setView(f.id);
            });

            this.banners.set(f.id, { text, line, floor: f });
            this.updateBanner(f.id);
        }
    }

    updateBanner(id) {
        const b = this.banners?.get(id);
        if (!b) return;
        const n = this.floorCounts[id] ?? 0;
        b.text.setText(`${floorTag(b.floor)} · ${b.floor.label}\n${b.floor.name}\n${n} staff`);
        if (b.text.input?.hitArea) b.text.input.hitArea.setSize(b.text.width, b.text.height);
        this.bannerW = Math.max(this.bannerW, b.text.width);
    }

    // counts = { [floorId]: n }
    setFloorCounts(counts) {
        this.floorCounts = { ...counts };
        if (!this.ready) return;
        for (const f of FLOORS) this.updateBanner(f.id);
    }

    // ---------- Paparan & kamera ----------

    normView(view) {
        if (view === 'building' || view === null || view === undefined) return 'building';
        const id = Number(view);
        return FLOORS.some((f) => f.id === id) ? id : 'building';
    }

    overviewBox() {
        const b = this.buildingBounds();
        const left = cornerF(FIRST_FLOOR, 1, GRID.rows).x - 70 - (this.bannerW || 560);
        const x0 = Math.min(b.x0, left) - 40;
        const x1 = b.x1 + 60;
        return { x: x0, y: b.y0 - 30, w: x1 - x0, h: b.y1 - b.y0 + 70 };
    }

    floorBox(f) {
        const x0 = cornerF(f, 1, GRID.rows).x - 16;
        const x1 = cornerF(f, GRID.cols, 1).x + 16;
        const y0 = cornerF(f, 1, 1).y - WALL_H - 14;
        const y1 = cornerF(f, GRID.cols, GRID.rows).y + SLAB_H + 10;
        return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    }

    // Aras di bawah titik dunia (x, y) dalam paparan bangunan (aras atas diuji dulu: ia dilukis di depan)
    floorAt(x, y) {
        for (let i = FLOORS.length - 1; i >= 0; i--) {
            const f = FLOORS[i];
            for (const lift of f.walls ? [0, 60, WALL_H] : [0, 60]) {
                const a = (x - ORIGIN.x) / (TILE.w / 2);
                const b = (y + lift - floorDy(f.id) - ORIGIN.y) / (TILE.h / 2);
                const c = (a + b) / 2;
                const r = (b - a) / 2;
                if (c >= 1 && c <= GRID.cols && r >= 1 && r <= GRID.rows) return f.id;
            }
        }
        return null;
    }

    fade(obj, alpha, instant) {
        if (!obj) return;
        this.tweens.killTweensOf(obj);
        if (instant) {
            obj.setAlpha(alpha);
            obj.setVisible(alpha > 0);
            return;
        }
        if (alpha > 0) obj.setVisible(true);
        this.tweens.add({
            targets: obj,
            alpha,
            duration: VIEW_MS * 0.6,
            onComplete: () => {
                if (alpha === 0) obj.setVisible(false);
            },
        });
    }

    // Nama + bubble staff dan label department: hanya dalam paparan aras
    setTextMode(on) {
        this.textMode = on;
        for (const label of this.deptLabels) label.setVisible(on);
        for (const s of this.staff.values()) this.applyTextMode(s);
    }

    applyTextMode(s) {
        s.name.setVisible(this.textMode);
        s.bubble.setVisible(this.textMode && (s.lastText ?? '') !== '');
    }

    // Staff hanya boleh diklik bila arasnya kelihatan
    syncStaffInput(s) {
        if (s.container.input) s.container.input.enabled = this.view === 'building' || s.floor === this.view;
    }

    // view: 'building' (semua aras) atau id aras (zoom penuh ke aras itu). Tween licin antara paparan.
    setView(view, { instant = false } = {}) {
        const v = this.normView(view);
        if (!this.ready) {
            this.view = v;
            return;
        }
        this.view = v;
        const overview = v === 'building';

        if (overview || instant) this.setTextMode(!overview);
        for (const f of FLOORS) this.fade(this.layers.get(f.id), overview || f.id === v ? 1 : 0, instant);
        this.fade(this.sky, overview ? 1 : 0, instant);
        for (const b of this.banners.values()) {
            this.fade(b.text, overview ? 1 : 0, instant);
            this.fade(b.line, overview ? 1 : 0, instant);
        }
        for (const s of this.staff.values()) this.syncStaffInput(s);

        const cam = this.cameras.main;
        const box = overview ? this.overviewBox() : this.floorBox(v);
        const zoom = Math.min(cam.width / box.w, cam.height / box.h);
        const to = { x: box.x + box.w / 2, y: box.y + box.h / 2, z: Math.log(zoom) };
        const from = this.camState ?? to;
        const apply = (t) => {
            const st = { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t, z: from.z + (to.z - from.z) * t };
            this.camState = st;
            cam.setZoom(Math.exp(st.z));
            cam.centerOn(st.x, st.y);
        };

        this.camTween?.stop();
        this.camTween = null;
        if (instant || !this.camState) {
            apply(1);
        } else {
            const proxy = { t: 0 };
            this.camTween = this.tweens.add({
                targets: proxy,
                t: 1,
                duration: VIEW_MS,
                ease: 'Sine.easeInOut',
                onUpdate: () => apply(proxy.t),
                onComplete: () => {
                    apply(1);
                    if (!overview && this.view === v) this.setTextMode(true);
                },
            });
        }

        this.onViewChange(v);
    }

    // Pilih staff (senarai Team / klik) dan zoom ke arasnya
    focusAgent(id) {
        this.selectedId = id;
        const s = this.staff.get(id);
        if (!s) return;
        const floor = s.climb ? s.climb.to : s.floor;
        if (this.view !== floor) this.setView(floor);
    }

    // ---------- Staff ----------

    styleOf(agent) {
        const style = AVATARS.includes(agent.avatar) ? agent.avatar : 'default';
        return this.textures.exists(texKey(style, 'fixed')) ? style : 'default';
    }

    moveToLayer(s, f) {
        this.put(f, s.container);
        s.depthKey = null;
    }

    spawn(agent, { silent = false } = {}) {
        const offset = offsetFor(agent.id);
        const style = this.styleOf(agent);
        const shirt = STYLE_SHIRT[style] ?? VENDOR_COLORS[agent.vendor] ?? 0x64748b;
        const hairs = STYLE_HAIR[style] ?? STYLE_HAIR.default;
        const hair = hairs[hashOf(agent.id) % hairs.length];
        const floor = floorOf('door');
        const start = spotFor('door');
        const p = tileCenterF(floor, start.c, start.r);

        const container = this.add.container(p.x + offset.x, p.y + offset.y);
        const shadow = this.add.ellipse(0, 3, 20, 7, 0x000000, 0.25);
        // 4 lapisan sprite: skin, hair, shirt diwarnakan (tint), fixed kekal. Kaki di y=46/48 frame.
        const skinColor = C.skins[hashOf(agent.id) % C.skins.length];
        const layers = ['fixed', 'skin', 'hair', 'shirt'].map((layer) =>
            this.add.sprite(0, 3, texKey(style, layer), 0).setOrigin(0.5, 46 / 48)
        );
        layers[1].setTint(skinColor);
        layers[2].setTint(hair);
        layers[3].setTint(shirt);
        const name = this.add
            .text(0, -47, agent.name ?? '', {
                fontFamily: FONT,
                fontSize: '10px',
                color: '#2a2219',
                backgroundColor: '#fffdf5cc',
                padding: { x: 3, y: 1 },
            })
            .setOrigin(0.5, 1);
        const bubble = this.add
            .text(0, -61, '', {
                fontFamily: FONT,
                fontSize: '11px',
                color: '#2a2219',
                backgroundColor: '#ffffff',
                padding: { x: 6, y: 3 },
                wordWrap: { width: 170 },
            })
            .setOrigin(0.5, 1)
            .setVisible(false);
        const bell = this.add.circle(15, -42, 6, 0xf5d37a).setStrokeStyle(1, 0x7a5a00).setVisible(false);
        const bellTxt = this.add
            .text(15, -42, '!', { fontFamily: FONT, fontSize: '9px', color: '#2a2219', fontStyle: 'bold' })
            .setOrigin(0.5)
            .setVisible(false);
        const errDot = this.add.circle(-15, -42, 5, 0xe53935).setVisible(false);

        container.add([shadow, ...layers, name, bubble, bell, bellTxt, errDot]);
        container.setSize(36, 58);
        container.setInteractive(new Phaser.Geom.Rectangle(-18, -50, 36, 56), Phaser.Geom.Rectangle.Contains);

        this.tweens.add({ targets: bell, scale: { from: 1, to: 1.25 }, duration: 500, yoyo: true, repeat: -1 });
        this.tweens.add({ targets: errDot, alpha: { from: 0.3, to: 1 }, duration: 400, yoyo: true, repeat: -1 });

        const s = {
            id: agent.id,
            agent,
            container,
            layers,
            style,
            act: null,
            facingLeft: false,
            shadow,
            name,
            bubble,
            bell,
            bellTxt,
            errDot,
            lastText: null,
            offset,
            floor,
            tile: { c: start.c, r: start.r },
            pos: { x: p.x + offset.x, y: p.y + offset.y },
            target: { floor, c: start.c, r: start.r },
            path: [],
            climb: null,
            dept: null,
            seated: false,
            seat: null,
            leaving: false,
            exitAt: null,
            depthKey: null,
        };

        container.on('pointerdown', () => {
            this.selectedId = agent.id;
            this.onSelect(agent.id);
            if (this.view === 'building') this.setView(s.climb ? s.climb.to : s.floor);
        });

        this.moveToLayer(s, floor);
        this.applyTextMode(s);
        this.syncStaffInput(s);

        // Pelawat penghantaran baru tiba di pintu: tekan loceng
        if (!silent && VISITOR_STYLES.includes(style) && agent.status !== 'ended') this.ringDoorbell();

        return s;
    }

    // Letak terus di destinasi (snapshot pertama: tak jalan dari pintu)
    teleport(s) {
        const t = s.target;
        const p = tileCenterF(t.floor, t.c, t.r);
        s.floor = t.floor;
        s.tile = { c: t.c, r: t.r };
        s.pos = { x: p.x + s.offset.x, y: p.y + s.offset.y };
        s.path = [];
        s.climb = null;
        s.container.setAlpha(1);
        s.container.setPosition(s.pos.x, s.pos.y);
        this.moveToLayer(s, s.floor);
        this.syncStaffInput(s);
    }

    // Berapa orang (selain s) sedang memegang tempat berdiri dalam department ini
    standOccupants(dept, except) {
        const f = floorOf(dept);
        return standsFor(dept).filter((cell) => {
            const owner = this.seatOwner.get(this.slotKey(f, cell));
            return owner !== undefined && owner !== except?.id;
        }).length;
    }

    // Ambil kerusi kosong (duduk), atau tempat berdiri kosong (bilik bermain, pantry...).
    // Department dengan had (pantry = 2): bila penuh, staff beratur di luar sampai ada kekosongan.
    // Kalau tiada tempat langsung = berdiri di spot. Department di aras lain: ikut tangga.
    walkTo(s, dept) {
        this.releaseSeat(s);

        const floor = floorOf(dept);
        const free = (cell) => !this.seatOwner.has(this.slotKey(floor, cell));
        const cap = capacityFor(dept);
        let slot = null;
        let sits = false;
        let queued = false;

        if (!s.leaving) {
            slot = seatsFor(dept).find(free) ?? null;
            sits = slot !== null;

            if (!slot) {
                if (cap !== null && this.standOccupants(dept, s) >= cap) {
                    slot = queueFor(dept).find(free) ?? null;
                    queued = slot !== null;
                } else {
                    const stands = standsFor(dept).filter(free);
                    // Pantry: pilih mesin rawak supaya semua jenama dapat giliran. Lain-lain ikut susunan.
                    slot = (cap !== null ? stands[Math.floor(Math.random() * stands.length)] : stands[0]) ?? null;
                }
            }
        }
        if (slot) {
            s.seat = this.slotKey(floor, slot);
            this.seatOwner.set(s.seat, s.id);
        }

        const target = slot ?? spotFor(dept);
        s.target = { floor, c: target.c, r: target.r };
        s.sitting = sits;
        s.queued = queued;
        s.standFlip = slot?.flip === true;
        s.standLabel = queued ? null : slot?.label ?? null;
        s.act = sits || queued ? null : slot?.act ?? null; // play | dart | drink | handover
        s.offset = sits ? { ...SEAT_SHIFT } : slot ? { x: 0, y: 0 } : offsetFor(s.id);
        s.dept = dept;
        s.exitAt = null;
        this.route(s);
    }

    // Laluan di aras semasa: terus ke sasaran, atau ke landing tangga kalau sasaran di aras lain.
    // Sedang naik/turun: laluan dikira bila sampai.
    route(s) {
        if (s.climb) return;
        const goal = s.floor === s.target.floor ? s.target : STAIRS.landing;
        s.path = findPath(s.tile, goal, this.blockedFor(s.floor), GRID.cols, GRID.rows) ?? [];
    }

    startClimb(s, time) {
        const i = floorIndex(s.floor);
        const j = floorIndex(s.target.floor);
        const next = FLOORS[i + Math.sign(j - i)];
        if (!next) {
            s.target = { ...s.target, floor: s.floor };
            this.route(s);
            return;
        }
        const land = tileCenterF(next.id, STAIRS.landing.c, STAIRS.landing.r);
        s.climb = {
            to: next.id,
            t0: time,
            from: { x: s.pos.x, y: s.pos.y },
            dest: { x: land.x + s.offset.x, y: land.y + s.offset.y },
            switched: false,
        };
        s.facingLeft = j < i;
    }

    // Naik/turun: tween lurus antara dua landing, pudar sedikit di tengah, tukar lapisan aras separuh jalan
    stepClimb(s, time) {
        const c = s.climb;
        const k = Math.min(1, (time - c.t0) / CLIMB_MS);
        s.pos.x = c.from.x + (c.dest.x - c.from.x) * k;
        s.pos.y = c.from.y + (c.dest.y - c.from.y) * k;
        s.container.setAlpha(1 - 0.4 * Math.sin(Math.PI * k));

        if (!c.switched && k >= 0.5) {
            c.switched = true;
            s.floor = c.to;
            this.moveToLayer(s, c.to);
            this.syncStaffInput(s);
        }
        if (k >= 1) {
            s.floor = c.to;
            s.tile = { c: STAIRS.landing.c, r: STAIRS.landing.r };
            s.climb = null;
            s.container.setAlpha(1);
            this.route(s);
        }
    }

    // Staff yang beratur: bila ada tempat kosong, naik ke giliran dan terus ke mesin.
    tryPromote(s) {
        const cap = capacityFor(s.dept);
        if (!s.queued || s.leaving || cap === null) return;
        if (this.standOccupants(s.dept, s) >= cap) return;

        this.walkTo(s, s.dept);
        s.lastText = null;
        this.updateVisuals(s, s.agent);
    }

    releaseSeat(s) {
        if (s.seat && this.seatOwner.get(s.seat) === s.id) {
            this.seatOwner.delete(s.seat);
        }
        s.seat = null;
    }

    // Dipanggil setiap kali state berubah. agents = senarai agent (tanpa yang dah ended).
    // opts.loaded: true bila snapshot sebenar dah dimuat. Render sebenar pertama letak staff terus di tempat.
    render(agents, opts = {}) {
        if (!this.ready) {
            this.pending = { agents, opts };

            return;
        }

        const initial = !this.initialDone && (opts.loaded ?? agents.length > 0);
        const seen = new Set();

        for (const a of agents) {
            seen.add(a.id);
            let s = this.staff.get(a.id);
            if (!s) {
                const place = initial && a.status !== 'ended';
                s = this.spawn(a, { silent: place });
                this.staff.set(a.id, s);
                if (place) {
                    s.agent = a;
                    this.walkTo(s, a.department ?? 'door');
                    this.teleport(s);
                }
            }
            s.agent = a;

            if (a.status === 'ended') {
                if (!s.leaving) {
                    s.leaving = true;
                    this.walkTo(s, 'door');
                }
            } else {
                if (s.leaving) {
                    s.leaving = false;
                    s.exitAt = null;
                }
                const target = a.department ?? s.dept ?? 'door';
                if (s.dept !== target) {
                    this.walkTo(s, target);
                }
            }

            this.updateVisuals(s, a);
        }

        // Agent yang hilang dari snapshot dianggap dah habis: keluar ikut pintu (melalui tangga)
        for (const [id, s] of this.staff) {
            if (!seen.has(id) && !s.leaving) {
                s.leaving = true;
                this.walkTo(s, 'door');
            }
        }

        if (initial) this.initialDone = true;
        this.deptState = this.computeDeptState(agents);
    }

    updateVisuals(s, a) {
        s.name.setText(a.name ?? '');
        s.name.setColor(a.status === 'error' ? '#b71c1c' : '#2a2219');

        // Gaya watak boleh ditukar oleh owner: tukar tekstur lapisan, kekalkan frame
        const style = this.styleOf(a);
        if (style !== s.style) {
            s.style = style;
            ['fixed', 'skin', 'hair', 'shirt'].forEach((layer, i) => s.layers[i].setTexture(texKey(style, layer)));
            const hairs = STYLE_HAIR[style] ?? STYLE_HAIR.default;
            s.layers[2].setTint(hairs[hashOf(a.id) % hairs.length]);
            s.layers[3].setTint(STYLE_SHIRT[style] ?? VENDOR_COLORS[a.vendor] ?? 0x64748b);
        }

        // Tiada tugas: bubble ikut bilik (Toilet break, Pantry, Chill...) sebelum status
        const visitorAtDoor = VISITOR_STYLES.includes(s.style) && s.dept === 'door' && !s.leaving && a.status !== 'ended';
        const text = a.current_task || (visitorAtDoor ? 'Ding dong! Delivery' : null) || (s.queued ? 'Beratur...' : s.standLabel) || DEPT_BUBBLE[s.dept] || STATUS_TEXT[a.status] || '';
        if (text !== s.lastText) {
            s.lastText = text;
            s.bubble.setText(text);
            if (text !== '' && this.textMode) {
                this.tweens.add({
                    targets: s.bubble,
                    scaleX: { from: 0.6, to: 1 },
                    scaleY: { from: 0.6, to: 1 },
                    duration: 200,
                    ease: 'Back.easeOut',
                });
            }
        }
        this.applyTextMode(s);

        const needsApproval = a.status === 'needs_approval';
        s.bell.setVisible(needsApproval);
        s.bellTxt.setVisible(needsApproval);
        s.errDot.setVisible(a.status === 'error');
    }

    computeDeptState(agents) {
        const state = {};
        for (const a of agents) {
            if (!a.department) continue;
            if (a.status === 'error') {
                state[a.department] = 'error';
            } else if (a.status === 'needs_approval' && state[a.department] !== 'error') {
                state[a.department] = 'approval';
            }
        }

        return state;
    }

    drawScreen(sc, time) {
        const g = sc.g;
        const state = this.deptState[sc.dept] ?? 'ok';
        g.clear();
        g.fillStyle(SCREEN_BG[state], 1).fillRect(sc.x - 5, sc.y, 10, 7);
        for (let i = 0; i < 4; i++) {
            const w = 2 + (Math.sin(time / 260 + sc.seed + i * 1.3) + 1) * 2.6;
            g.fillStyle(CODE_FG[state], 0.9).fillRect(sc.x - 4, sc.y + 1 + i * 1.6, w, 1);
        }
    }

    // Frame sprite: 0-1 idle, 2-5 jalan, 6-7 duduk taip. Semua lapisan guna frame sama.
    animateFigure(s, time, moving) {
        let frame;
        if (moving) {
            frame = 2 + (Math.floor(time / 130) % 4);
        } else if (s.seated) {
            // Duduk membelakangkan kamera, menaip menghadap meja
            frame = 8 + (Math.floor(time / 140) % 2);
        } else if (s.activity === 'play') {
            // Snooker / ping-pong / foosball: tangan ke depan bergilir (frame 10-11)
            frame = 10 + (Math.floor(time / 260) % 2);
        } else if (s.activity === 'dart') {
            // Lontar dart: tarik (12) lama, lontar (13) sekejap
            frame = 12 + (Math.floor(time / 450) % 3 === 2 ? 1 : 0);
        } else if (s.activity === 'handover') {
            // Serah bungkusan / makanan ke kaunter: tangan ke depan bergilir perlahan (frame 10-11)
            frame = 10 + (Math.floor(time / 320) % 2);
        } else if (s.activity === 'drink') {
            // Minum di pantry (frame 14-15)
            frame = 14 + (Math.floor(time / 900) % 2);
        } else {
            frame = Math.floor(time / 700) % 2;
        }

        for (const layer of s.layers) {
            layer.setFrame(frame);
            layer.setFlipX(s.seated ? false : s.facingLeft);
        }
    }

    update(time, delta) {
        if (!this.ready) return;

        this.screenTimer += delta;
        if (this.screenTimer > 120) {
            this.screenTimer = 0;
            for (const sc of this.screens) {
                if (this.layerOf(sc.floor).visible) this.drawScreen(sc, time);
            }
        }

        // Giliran pantry: setiap 0.6s, staff yang beratur naik bila ada kekosongan
        this.queueTimer = (this.queueTimer ?? 0) + delta;
        if (this.queueTimer > 600) {
            this.queueTimer = 0;
            for (const s of this.staff.values()) {
                if (s.queued) this.tryPromote(s);
            }
        }

        const step = (WALK_SPEED * delta) / 1000;
        const doorFloor = floorOf('door');
        const doorSpot = spotFor('door');

        for (const [id, s] of this.staff) {
            let moving = false;

            if (s.climb) {
                moving = true;
                this.stepClimb(s, time);
            } else if (s.path.length > 0) {
                moving = true;
                const next = s.path[0];
                const t = tileCenterF(s.floor, next.c, next.r);
                const tx = t.x + s.offset.x;
                const ty = t.y + s.offset.y;
                const dx = tx - s.pos.x;
                const dy = ty - s.pos.y;
                const dist = Math.hypot(dx, dy);
                if (Math.abs(dx) > 0.5) s.facingLeft = dx < 0;

                if (dist <= step) {
                    s.pos = { x: tx, y: ty };
                    s.tile = next;
                    s.path.shift();
                } else {
                    s.pos.x += (dx / dist) * step;
                    s.pos.y += (dy / dist) * step;
                }
            } else if (s.target && s.target.floor !== s.floor) {
                // Sampai landing (atau tiada laluan): naik/turun satu aras
                moving = true;
                this.startClimb(s, time);
            }

            // Resepsionis sampai ke department lain: hantar arahan (sampul surat), sekali setiap ketibaan
            if (s.style === 'recep' && s.wasMoving && !moving && !s.leaving && s.dept && s.dept !== 'frontdesk' && time - (s.noteAt ?? -1e9) > 2500) {
                s.noteAt = time;
                this.sendNote(s);
            }
            s.wasMoving = moving;

            s.seated = !moving && !s.leaving && s.seat !== null && s.sitting === true;
            s.activity = !moving && !s.leaving && s.seat !== null && s.sitting !== true ? s.act : null;
            if (!moving && s.seat !== null && s.sitting !== true) s.facingLeft = s.standFlip === true;
            this.animateFigure(s, time, moving);

            const bob = moving ? Math.sin(time / 90) * 1.2 : 0;
            s.container.setPosition(s.pos.x, s.pos.y + bob);
            const depth = s.tile.c + s.tile.r + 0.5;
            if (s.depthKey !== depth) {
                s.depthKey = depth;
                s.container.setDepth(depth);
            }

            const selected = id === this.selectedId;
            if (s.selectedShown !== selected) {
                s.selectedShown = selected;
                s.shadow.setFillStyle(selected ? 0xfbbc05 : 0x000000, selected ? 0.75 : 0.25);
            }

            // Sampai pintu sambil keluar: tunggu 10s, kemudian hilang
            if (!moving && s.leaving && s.floor === doorFloor && s.tile.c === doorSpot.c && s.tile.r === doorSpot.r) {
                if (s.exitAt === null) s.exitAt = time + (VISITOR_STYLES.includes(s.style) ? VISITOR_EXIT_DELAY_MS : EXIT_DELAY_MS);
                if (time >= s.exitAt) {
                    this.releaseSeat(s);
                    s.container.destroy();
                    this.staff.delete(id);
                }
            }
        }

        this.updateParcels(delta);
    }
}
