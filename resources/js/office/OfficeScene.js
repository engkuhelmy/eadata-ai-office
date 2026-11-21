import Phaser from 'phaser';
import { GRID, TILE, ORIGIN, CANVAS, DEPARTMENTS, DECOR, VENDOR_COLORS, blockedTiles, spotFor } from './layout';
import { findPath } from './pathfinding';

const WALK_SPEED = 110; // px per saat
const EXIT_DELAY_MS = 10000; // staff hilang 10s lepas sampai pintu
const WALL_H = 130;
const BLOCKED = blockedTiles();

const C = {
    floorA: 0xd9a36a,
    floorB: 0xc98f58,
    floorEdge: 0x9c6b3c,
    rugRed: 0xa84b32,
    rugBlue: 0x3b6e8f,
    wall: 0xead7b4,
    wallTrim: 0x8b5e3c,
    glass: 0xffe3a0,
    glassHi: 0xfff6d6,
    frame: 0x7a4f2e,
    board: 0xf8fafc,
    cork: 0xc8a165,
    skin: 0xf2cfae,
    legs: 0x2a2a3a,
    plant: 0x3f8f4a,
    pot: 0xa0522d,
    skins: [0xf2cfae, 0xd9a577, 0x8d5524, 0xf5d0b0],
    chair: 0x3b3b46,
};

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
};

const SCREEN_BG = { ok: 0x14321f, approval: 0x3d2a08, error: 0x3d0f0f };
const CODE_FG = { ok: 0x6ee7a0, approval: 0xfbbf24, error: 0xff7070 };
const HAIR = [0x2a2219, 0x6d4c2a, 0x1f2937, 0xa16207, 0x3f3f46, 0x92400e];
const BOOK = [0xb91c1c, 0x1d4ed8, 0x15803d, 0xca8a04, 0x7c3aed, 0xdb2777];

const STATUS_TEXT = {
    active: 'Kerja...',
    idle: '',
    error: 'Ada error!',
    needs_approval: 'Perlu approval',
    rate_limited: 'Rehat dulu',
    ended: '',
};

// Grid corner (c, r) → skrin (isometric)
export function corner(c, r) {
    return {
        x: ORIGIN.x + ((c - r) * TILE.w) / 2,
        y: ORIGIN.y + ((c + r) * TILE.h) / 2,
    };
}

// Titik tengah tile (c, r) → skrin
export function tileCenter(c, r) {
    return corner(c + 0.5, r + 0.5);
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

function outline(g, points, color, width = 1, alpha = 1) {
    g.lineStyle(width, color, alpha);
    g.beginPath();
    g.moveTo(points[0].x, points[0].y);
    for (const p of points.slice(1)) {
        g.lineTo(p.x, p.y);
    }
    g.closePath();
    g.strokePath();
}

// Kotak isometric di atas tile (c, r) setinggi h
function drawBox(g, c, r, h, st) {
    const { x, y } = tileCenter(c, r);
    const hw = TILE.w / 2;
    const hh = TILE.h / 2;

    polygon(g, [
        { x: x - hw, y: y - h },
        { x, y: y - h - hh },
        { x: x + hw, y: y - h },
        { x, y: y - h + hh },
    ], st.top);
    polygon(g, [
        { x: x - hw, y: y - h },
        { x, y: y - h + hh },
        { x, y: y + hh },
        { x: x - hw, y },
    ], st.left);
    polygon(g, [
        { x: x + hw, y: y - h },
        { x, y: y - h + hh },
        { x, y: y + hh },
        { x: x + hw, y },
    ], st.right);

    return { x, y, hw, hh };
}

// Titik pada dinding: wall 'A' sepanjang c (r=1), wall 'B' sepanjang r (c=1). v = ketinggian.
function wallPt(wall, u, v) {
    const p = wall === 'A' ? corner(u, 1) : corner(1, u);

    return { x: p.x, y: p.y - v };
}

function wallQuad(g, wall, u0, u1, v0, v1, color, alpha = 1) {
    polygon(g, [
        wallPt(wall, u0, v0),
        wallPt(wall, u1, v0),
        wallPt(wall, u1, v1),
        wallPt(wall, u0, v1),
    ], color, alpha);
}

function wallOutline(g, wall, u0, u1, v0, v1, color, width = 2) {
    outline(g, [
        wallPt(wall, u0, v0),
        wallPt(wall, u1, v0),
        wallPt(wall, u1, v1),
        wallPt(wall, u0, v1),
    ], color, width);
}

function tilePoly(g, c, r, color, alpha) {
    const { x, y } = tileCenter(c, r);
    const hw = TILE.w / 2;
    const hh = TILE.h / 2;

    polygon(g, [
        { x, y: y - hh },
        { x: x + hw, y },
        { x, y: y + hh },
        { x: x - hw, y },
    ], color, alpha);
}

export default class OfficeScene extends Phaser.Scene {
    constructor() {
        super('office');
        this.staff = new Map();
        this.screens = [];
        this.deptState = {};
        this.pending = null;
        this.ready = false;
        this.screenTimer = 0;
        this.onSelect = () => {};
    }

    preload() {
        // Sprite sheet staff: 4 lapisan (fixed, skin, hair, shirt), 8 frame 32x48
        for (const layer of ['fixed', 'skin', 'hair', 'shirt']) {
            this.load.spritesheet(`staff_${layer}`, `/assets/office/staff_${layer}.png`, { frameWidth: 32, frameHeight: 48 });
        }
        for (const name of ['wall_window_a', 'wall_window_b', 'wall_board_a', 'wall_cork_b', 'wall_poster_a1', 'wall_poster_a2', 'wall_poster_b', 'wall_logo_b']) {
            this.load.image(name, `/assets/office/${name}.png`);
        }
        for (const name of ['floor_a', 'floor_b', 'desk', 'chair', 'plant', 'shelf', 'cooler', 'sofa', 'machine', 'server', 'pong', 'foos', 'table', 'reception', 'bell']) {
            this.load.image(name, `/assets/office/${name}.png`);
        }
    }

    // Letak sprite furniture pada tile (c, r). Anchor: bucu bawah tile (tengah + 14px).
    placeSprite(key, c, r, depth = c + r, dy = 14) {
        const { x, y } = tileCenter(c, r);

        return this.add.image(x, y + dy, key).setOrigin(0.5, 1).setDepth(depth);
    }

    create() {
        this.floorGfx = this.add.graphics().setDepth(-1000);
        this.wallGfx = this.add.graphics().setDepth(-900);
        this.drawFloor();
        this.drawWalls();
        this.drawStatic();
        this.drawLabels();
        this.addAmbient();

        this.lighting = this.add
            .rectangle(0, 0, CANVAS.w, CANVAS.h, 0xffb86b, 0.05)
            .setOrigin(0, 0)
            .setDepth(100000);

        this.ready = true;

        if (this.pending) {
            this.render(this.pending);
            this.pending = null;
        }
    }

    drawFloor() {
        const g = this.floorGfx;

        // Lantai: sprite kayu checker (di bawah permaidani)
        for (let r = 1; r < GRID.rows; r++) {
            for (let c = 1; c < GRID.cols; c++) {
                const { x, y } = tileCenter(c, r);
                this.add.image(x, y, (c + r) % 2 === 0 ? 'floor_a' : 'floor_b').setDepth(-1001);
            }
        }

        // Permaidani: meeting (merah) dan break room (biru)
        for (let r = 5; r <= 7; r++) for (let c = 8; c <= 12; c++) tilePoly(g, c, r, C.rugRed, 0.22);
        for (let r = 11; r <= 14; r++) for (let c = 14; c <= 19; c++) tilePoly(g, c, r, C.rugBlue, 0.16);
    }

    drawWalls() {
        const g = this.wallGfx;

        // Dinding belakang
        polygon(g, [wallPt('A', 1, 0), wallPt('A', GRID.cols, 0), wallPt('A', GRID.cols, WALL_H), wallPt('A', 1, WALL_H)], C.wall);
        polygon(g, [wallPt('B', 1, 0), wallPt('B', GRID.rows, 0), wallPt('B', GRID.rows, WALL_H), wallPt('B', 1, WALL_H)], C.wall);
        wallQuad(g, 'A', 1, GRID.cols, 0, 6, C.wallTrim);
        wallQuad(g, 'B', 1, GRID.rows, 0, 6, C.wallTrim);

        // Panel kayu bawah dinding (wainscot)
        wallQuad(g, 'A', 1, GRID.cols, 6, 30, 0xd8b88a);
        wallQuad(g, 'B', 1, GRID.rows, 6, 30, 0xd8b88a);
        outline(g, [wallPt('A', 1, 30), wallPt('A', GRID.cols, 30)], 0x9c6b3c, 2);
        outline(g, [wallPt('B', 1, 30), wallPt('B', GRID.rows, 30)], 0x9c6b3c, 2);

        // Hiasan dinding: sprite pixel art yang di-shear ikut dinding
        const windowsA = [2, 6, 18];
        const windowsB = [2, 10.4];
        for (const u of windowsA) this.wallSprite('wall_window_a', 'A', u, 106);
        for (const u of windowsB) this.wallSprite('wall_window_b', 'B', u, 106);
        this.wallSprite('wall_board_a', 'A', 9, 100); // atas meeting table
        this.wallSprite('wall_cork_b', 'B', 5.5, 96); // marketing plan
        this.wallSprite('wall_poster_a1', 'A', 12.6, 102);
        this.wallSprite('wall_poster_a2', 'A', 20.5, 102);
        this.wallSprite('wall_poster_b', 'B', 9, 102);
        this.wallSprite('wall_logo_b', 'B', 13.2, 92); // logo di sebelah reception

        // Cahaya tingkap di lantai (additive, lembut)
        const light = this.add.graphics().setDepth(-950).setBlendMode(Phaser.BlendModes.ADD);
        for (const u of windowsA) {
            polygon(light, [corner(u, 1), corner(u + 1.6, 1), corner(u + 0.1, 4.5), corner(u - 1.5, 4.5)], 0xffd890, 0.13);
        }
        for (const u of windowsB) {
            polygon(light, [corner(1, u), corner(1, u + 1.6), corner(4.5, u + 0.1), corner(4.5, u - 1.5)], 0xffd890, 0.13);
        }

        // Jam dinding
        const clock = wallPt('A', 16.5, 100);
        g.fillStyle(0xfffdf5, 1).fillCircle(clock.x, clock.y, 9);
        g.lineStyle(2, C.frame, 1).strokeCircle(clock.x, clock.y, 9);
        g.lineStyle(1.5, 0x2a2219, 1);
        g.lineBetween(clock.x, clock.y, clock.x, clock.y - 6);
        g.lineBetween(clock.x, clock.y, clock.x + 4, clock.y + 1);
    }

    // Sprite dinding: A (origin kiri-atas) di u0, B (origin kanan-atas) di u0, ketinggian atas = vTop
    wallSprite(key, wall, u0, vTop) {
        const p = wallPt(wall, u0, vTop);

        return this.add.image(p.x, p.y, key).setOrigin(wall === 'A' ? 0 : 1, 0).setDepth(-890);
    }

    drawLabels() {
        for (const dept of Object.values(DEPARTMENTS)) {
            const cell = dept.cells[0];
            const { x, y } = cell ? tileCenter(cell.c, cell.r) : tileCenter(dept.spot.c, dept.spot.r);

            this.add
                .text(x, y - 46, dept.label, {
                    fontFamily: 'system-ui, sans-serif',
                    fontSize: '11px',
                    color: '#2a2219',
                    backgroundColor: '#fffdf5',
                    padding: { x: 6, y: 3 },
                })
                .setOrigin(0.5)
                .setDepth(50000);
        }
    }

    // Furniture statik + skrin monitor (skrin dikemaskini dalam update)
    drawStatic() {
        // Kerusi di spot setiap department meja (staff duduk di sini, di belakang sprite)
        for (const dept of Object.values(DEPARTMENTS)) {
            if (!dept.cells.some((cell) => cell.kind === 'desk')) continue;
            // Kerusi pejabat (sprite), pangkal di bawah kaki staff
            this.placeSprite('chair', dept.spot.c, dept.spot.r, dept.spot.c + dept.spot.r - 0.2, 6);
        }

        for (const [key, dept] of Object.entries(DEPARTMENTS)) {
            for (const cell of dept.cells) {
                const { x, y } = tileCenter(cell.c, cell.r);
                this.placeSprite(cell.kind, cell.c, cell.r);

                if (cell.kind === 'desk') {
                    // Skrin monitor animasi (kawasan 10x7 pada sprite desk), plus lampu berdenyut
                    const screen = this.add.graphics().setDepth(cell.c + cell.r + 0.2);
                    this.screens.push({ g: screen, x, y: y - 29, dept: key, seed: hashOf(`${cell.c},${cell.r}`) % 7 });

                    const lamp = this.add
                        .circle(x + 8, y - 18, 14, 0xffc46b, 0.12)
                        .setBlendMode(Phaser.BlendModes.ADD)
                        .setDepth(cell.c + cell.r + 0.3);
                    this.tweens.add({ targets: lamp, alpha: { from: 0.05, to: 0.18 }, duration: 1400 + (cell.c * 90) % 500, yoyo: true, repeat: -1 });
                }
            }
        }

        for (const item of DECOR) {
            for (const cell of item.cells) {
                if (item.kind === 'plant') {
                    this.drawPlant(cell.c, cell.r);
                    continue;
                }

                const { x, y } = tileCenter(cell.c, cell.r);
                this.placeSprite(item.kind, cell.c, cell.r);

                if (item.kind === 'server') {
                    // LED berkelip pada muka kiri rak
                    for (let i = 0; i < 4; i++) {
                        const led = this.add.circle(x - 22 + i * 5, y - 33 + i * 2.5, 1.6, i % 2 ? 0x22c55e : 0xfbbf24);
                        led.setDepth(cell.c + cell.r + 0.1);
                        this.tweens.add({ targets: led, alpha: { from: 0.2, to: 1 }, duration: 350 + i * 170, yoyo: true, repeat: -1 });
                    }
                }
            }
        }
    }

    drawPlant(c, r) {
        const { x, y } = tileCenter(c, r);
        const plant = this.add.image(x, y + 8, 'plant').setOrigin(0.5, 1).setDepth(c + r);
        this.tweens.add({ targets: plant, angle: { from: -1.5, to: 1.5 }, duration: 2200, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
    }

    addAmbient() {
        // Dust motes dalam cahaya tingkap
        for (let i = 0; i < 14; i++) {
            const x = 380 + Math.random() * 420;
            const y = 150 + Math.random() * 200;
            const mote = this.add.circle(x, y, 1.6, 0xfff7d6, 0.6).setDepth(40000);
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

        // Asap kopi dan gelembung water cooler
        const machine = tileCenter(20, 2);
        const cooler = tileCenter(20, 13);
        this.time.addEvent({
            delay: 800,
            loop: true,
            callback: () => {
                this.puff(machine.x - 3, machine.y - 40, 0xf5f5f4, 26, 1600);
                this.puff(cooler.x, cooler.y - 42, 0xbfe9ff, 18, 1000);
            },
        });
    }

    puff(x, y, color, rise, duration) {
        const dot = this.add.circle(x + (Math.random() * 6 - 3), y, 3, color, 0.7).setDepth(9000);
        this.tweens.add({
            targets: dot,
            y: y - rise,
            alpha: 0,
            scale: 2,
            duration,
            onComplete: () => dot.destroy(),
        });
    }

    spawn(agent) {
        const offset = offsetFor(agent.id);
        const shirt = VENDOR_COLORS[agent.vendor] ?? 0x64748b;
        const hair = HAIR[hashOf(agent.id) % HAIR.length];
        const start = spotFor('door');
        const p = tileCenter(start.c, start.r);

        const container = this.add.container(p.x + offset.x, p.y + offset.y);
        const shadow = this.add.ellipse(0, 3, 20, 7, 0x000000, 0.25);
        // 4 lapisan sprite: skin, hair, shirt diwarnakan (tint), fixed kekal. Kaki di y=46/48 frame.
        const skinColor = C.skins[hashOf(agent.id) % C.skins.length];
        const layers = ['fixed', 'skin', 'hair', 'shirt'].map((layer) =>
            this.add.sprite(0, 3, `staff_${layer}`, 0).setOrigin(0.5, 46 / 48)
        );
        layers[1].setTint(skinColor);
        layers[2].setTint(hair);
        layers[3].setTint(shirt);
        const name = this.add
            .text(0, -47, agent.name ?? '', {
                fontFamily: 'system-ui, sans-serif',
                fontSize: '10px',
                color: '#2a2219',
                backgroundColor: '#fffdf5cc',
                padding: { x: 3, y: 1 },
            })
            .setOrigin(0.5, 1);
        const bubble = this.add
            .text(0, -61, '', {
                fontFamily: 'system-ui, sans-serif',
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
            .text(15, -42, '!', { fontFamily: 'system-ui, sans-serif', fontSize: '9px', color: '#2a2219', fontStyle: 'bold' })
            .setOrigin(0.5)
            .setVisible(false);
        const errDot = this.add.circle(-15, -42, 5, 0xe53935).setVisible(false);

        container.add([shadow, ...layers, name, bubble, bell, bellTxt, errDot]);
        container.setSize(36, 58);
        container.setInteractive(new Phaser.Geom.Rectangle(-18, -50, 36, 56), Phaser.Geom.Rectangle.Contains);
        container.on('pointerdown', () => this.onSelect(agent.id));

        this.tweens.add({ targets: bell, scale: { from: 1, to: 1.25 }, duration: 500, yoyo: true, repeat: -1 });
        this.tweens.add({ targets: errDot, alpha: { from: 0.3, to: 1 }, duration: 400, yoyo: true, repeat: -1 });

        return {
            id: agent.id,
            agent,
            container,
            layers,
            facingLeft: false,
            shadow,
            name,
            bubble,
            bell,
            bellTxt,
            errDot,
            lastText: null,
            offset,
            tile: { c: start.c, r: start.r },
            pos: { x: p.x + offset.x, y: p.y + offset.y },
            path: [],
            dept: null,
            seated: false,
            leaving: false,
            exitAt: null,
        };
    }

    walkTo(s, dept) {
        const target = spotFor(dept);
        const path = findPath(s.tile, target, BLOCKED, GRID.cols, GRID.rows);

        s.path = path ?? [];
        s.dept = dept;
        s.exitAt = null;
    }

    // Dipanggil setiap kali state berubah. agents = senarai agent (tanpa yang dah ended).
    render(agents) {
        if (!this.ready) {
            this.pending = agents;

            return;
        }

        const seen = new Set();

        for (const a of agents) {
            seen.add(a.id);
            let s = this.staff.get(a.id);
            if (!s) {
                s = this.spawn(a);
                this.staff.set(a.id, s);
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

        // Agent yang hilang dari snapshot dianggap dah habis: keluar ikut pintu
        for (const [id, s] of this.staff) {
            if (!seen.has(id) && !s.leaving) {
                s.leaving = true;
                this.walkTo(s, 'door');
            }
        }

        this.deptState = this.computeDeptState(agents);
    }

    updateVisuals(s, a) {
        s.name.setText(a.name ?? '');
        s.name.setColor(a.status === 'error' ? '#b71c1c' : '#2a2219');

        const text = a.current_task || STATUS_TEXT[a.status] || '';
        s.bubble.setVisible(text !== '');
        if (text !== s.lastText) {
            s.lastText = text;
            s.bubble.setText(text);
            if (text !== '') {
                this.tweens.add({
                    targets: s.bubble,
                    scaleX: { from: 0.6, to: 1 },
                    scaleY: { from: 0.6, to: 1 },
                    duration: 200,
                    ease: 'Back.easeOut',
                });
            }
        }

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
            frame = 6 + (Math.floor(time / 120) % 2);
        } else {
            frame = Math.floor(time / 700) % 2;
        }

        for (const layer of s.layers) {
            layer.setFrame(frame);
            layer.setFlipX(s.facingLeft);
        }
    }

    update(time, delta) {
        if (!this.ready) return;

        this.screenTimer += delta;
        if (this.screenTimer > 120) {
            this.screenTimer = 0;
            for (const sc of this.screens) this.drawScreen(sc, time);
        }

        const step = (WALK_SPEED * delta) / 1000;
        const doorSpot = spotFor('door');

        for (const [id, s] of this.staff) {
            const moving = s.path.length > 0;

            if (moving) {
                const next = s.path[0];
                const t = tileCenter(next.c, next.r);
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
            }

            s.seated = !moving && !s.leaving && (DEPARTMENTS[s.dept]?.cells ?? []).some((c) => c.kind === 'desk');
            this.animateFigure(s, time, moving);

            const bob = moving ? Math.sin(time / 90) * 1.2 : 0;
            s.container.setPosition(s.pos.x, s.pos.y + bob);
            s.container.setDepth(s.tile.c + s.tile.r + 0.5);

            // Sampai pintu sambil keluar: tunggu 10s, kemudian hilang
            if (!moving && s.leaving && s.tile.c === doorSpot.c && s.tile.r === doorSpot.r) {
                if (s.exitAt === null) s.exitAt = time + EXIT_DELAY_MS;
                if (time >= s.exitAt) {
                    s.container.destroy();
                    this.staff.delete(id);
                }
            }
        }
    }
}
