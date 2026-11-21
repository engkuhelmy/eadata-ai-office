// Layout pejabat ikut gambar rujukan: grid 22x16, tingkat dua dinding belakang.
// Baris r=0 dan lajur c=0 ialah luar dinding (disekat).
// cells = furniture yang disekat. kind tentukan rupa (desk, table, sofa, cooler, dll).
// spot = tile tempat staff berdiri bila sampai ke department.

export const GRID = { cols: 22, rows: 16 };
export const TILE = { w: 56, h: 28 };
export const ORIGIN = { x: 470, y: 150 };
export const CANVAS = { w: 1280, h: 720 };

export const DEPARTMENTS = {
    door: {
        label: 'Reception',
        spot: { c: 1, r: 14 },
        cells: [{ c: 3, r: 13, kind: 'reception' }, { c: 4, r: 13, kind: 'reception' }],
    },
    kanban: {
        label: 'Marketing Plan',
        spot: { c: 2, r: 8 },
        cells: [],
    },
    frontend: {
        label: 'Coding',
        spot: { c: 3, r: 5 },
        cells: [{ c: 2, r: 3, kind: 'desk' }, { c: 3, r: 3, kind: 'desk' }, { c: 4, r: 3, kind: 'desk' }],
    },
    backend: {
        label: 'Coding',
        spot: { c: 7, r: 5 },
        cells: [{ c: 6, r: 3, kind: 'desk' }, { c: 7, r: 3, kind: 'desk' }, { c: 8, r: 3, kind: 'desk' }],
    },
    qa: {
        label: 'Debugging',
        spot: { c: 12, r: 5 },
        cells: [{ c: 12, r: 3, kind: 'desk' }, { c: 13, r: 3, kind: 'desk' }],
    },
    meeting: {
        label: 'Client Meeting',
        spot: { c: 10, r: 6 },
        seats: [{ c: 9, r: 5 }, { c: 10, r: 5 }, { c: 11, r: 5 }],
        cells: [
            { c: 9, r: 3, kind: 'table' }, { c: 10, r: 3, kind: 'table' }, { c: 11, r: 3, kind: 'table' },
            { c: 9, r: 4, kind: 'table' }, { c: 10, r: 4, kind: 'table' }, { c: 11, r: 4, kind: 'table' },
        ],
    },
    approval: {
        label: 'Reviewing PR',
        spot: { c: 15, r: 6 },
        cells: [{ c: 15, r: 5, kind: 'bell' }],
    },
    research: {
        label: 'Design Draft',
        spot: { c: 16, r: 10 },
        cells: [{ c: 15, r: 8, kind: 'desk' }, { c: 16, r: 8, kind: 'desk' }, { c: 17, r: 8, kind: 'desk' }],
    },
    deploy: {
        label: 'Support Call',
        spot: { c: 7, r: 11 },
        cells: [{ c: 6, r: 9, kind: 'desk' }, { c: 7, r: 9, kind: 'desk' }, { c: 8, r: 9, kind: 'desk' }],
    },
    ops: {
        label: 'Onboarding',
        spot: { c: 19, r: 11 },
        cells: [{ c: 19, r: 9, kind: 'desk' }, { c: 20, r: 9, kind: 'desk' }],
    },
    coffee: {
        label: 'Coffee',
        spot: { c: 19, r: 4 },
        cells: [{ c: 20, r: 2, kind: 'machine' }, { c: 21, r: 2, kind: 'machine' }],
    },
    water_cooler: {
        label: 'Break time',
        spot: { c: 18, r: 13 },
        cells: [
            { c: 16, r: 13, kind: 'sofa_blue' }, { c: 17, r: 13, kind: 'sofa_red' },
            { c: 20, r: 13, kind: 'cooler' },
        ],
    },
    // Bilik bermain: staff yang "chill" (idle lebih 2 minit) berdiri sekeliling meja ping-pong dan foosball.
    // stands = tempat berdiri (flip = menghadap kiri). Bukan kerusi, jadi tidak duduk.
    playroom: {
        label: 'Game Room',
        spot: { c: 11, r: 12 },
        cells: [
            { c: 12, r: 12, kind: 'pong' }, { c: 13, r: 12, kind: 'pong' },
            { c: 12, r: 13, kind: 'pong' }, { c: 13, r: 13, kind: 'pong' },
            { c: 11, r: 15, kind: 'foos' }, { c: 12, r: 15, kind: 'foos' },
        ],
        stands: [
            { c: 11, r: 12 }, { c: 11, r: 13 }, { c: 12, r: 11 }, { c: 13, r: 11 },
            { c: 14, r: 12, flip: true }, { c: 12, r: 14 }, { c: 13, r: 14, flip: true },
            { c: 10, r: 14 }, { c: 11, r: 14 }, { c: 10, r: 15 },
        ],
    },
};

// Dekor: hiasan yang juga disekat (kecuali yang tiada cells)
export const DECOR = [
    { kind: 'shelf', cells: [{ c: 4, r: 1 }, { c: 5, r: 1 }] },
    { kind: 'shelf', cells: [{ c: 1, r: 9 }, { c: 1, r: 10 }] },
    // Partition separuh tinggi: bilik reception (kiri bawah) dan break room (kanan bawah)
    { kind: 'partition_a', cells: [{ c: 2, r: 11 }, { c: 3, r: 11 }, { c: 4, r: 11 }, { c: 15, r: 12 }, { c: 17, r: 12 }] },
    { kind: 'partition_a_logo', cells: [{ c: 16, r: 12 }] },
    { kind: 'partition_b', cells: [{ c: 5, r: 13 }, { c: 14, r: 13 }, { c: 14, r: 14 }] },
    { kind: 'partition_b_logo', cells: [{ c: 5, r: 12 }] },
    { kind: 'plant', cells: [{ c: 1, r: 4 }] },
    { kind: 'plant', cells: [{ c: 21, r: 6 }] },
    { kind: 'plant', cells: [{ c: 13, r: 15 }] },
    { kind: 'plant', cells: [{ c: 1, r: 15 }] },
    { kind: 'server', cells: [{ c: 21, r: 9 }, { c: 21, r: 10 }] },
];

export const VENDOR_COLORS = {
    claude: 0xd97757,
    codex: 0x10a37f,
    hermes: 0x8b5cf6,
    antigravity: 0x4285f4,
    generic: 0x64748b,
};

// Semua tile yang disekat: luar dinding, furniture, dan dekor
export function blockedTiles() {
    const set = new Set();

    for (let c = 0; c < GRID.cols; c++) set.add(`${c},0`);
    for (let r = 0; r < GRID.rows; r++) set.add(`0,${r}`);

    for (const dept of Object.values(DEPARTMENTS)) {
        for (const cell of dept.cells) {
            set.add(`${cell.c},${cell.r}`);
        }
    }
    for (const item of DECOR) {
        for (const cell of item.cells) {
            set.add(`${cell.c},${cell.r}`);
        }
    }

    return set;
}

// Kerusi untuk duduk: satu di depan setiap meja (r + 1), atau senarai seats eksplisit
export function seatsFor(department) {
    const dept = DEPARTMENTS[department];
    if (!dept) return [];
    if (dept.seats) return dept.seats;

    return dept.cells.filter((cell) => cell.kind === 'desk').map((cell) => ({ c: cell.c, r: cell.r + 1 }));
}

// Tempat berdiri (bilik bermain)
export function standsFor(department) {
    return DEPARTMENTS[department]?.stands ?? [];
}

export function allSeats() {
    return Object.keys(DEPARTMENTS).flatMap((key) => seatsFor(key));
}

export function spotFor(department) {
    return (DEPARTMENTS[department] ?? DEPARTMENTS.door).spot;
}
