// Layout pejabat: grid 28x20 (sayap kanan untuk pantry dan toilet, sayap bawah untuk chill room).
// Baris r=0 dan lajur c=0 ialah luar dinding (disekat).
// cells = furniture yang disekat. kind tentukan rupa (desk, table, sofa, cooler, dll).
// spot = tile tempat staff berdiri bila sampai ke department.
// seats = kerusi (duduk, nampak dari belakang). stands = tempat berdiri; act = aktiviti
//   ('play' snooker/ping-pong/foosball, 'dart' lontar dart, 'drink' minum). flip = menghadap kiri.

export const GRID = { cols: 28, rows: 20 };
export const TILE = { w: 56, h: 28 };
export const ORIGIN = { x: 600, y: 150 };
export const CANVAS = { w: 1440, h: 860 };

export const DEPARTMENTS = {
    door: {
        label: 'Reception',
        spot: { c: 1, r: 14 },
        cells: [{ c: 3, r: 13, kind: 'reception' }, { c: 4, r: 13, kind: 'reception' }],
    },
    // Kaunter reception: pelawat (rider/kurier) berdiri di depan kaunter (act 'handover', maksimum 2 serentak,
    // selebihnya beratur). Resepsionis berdiri di belakang kaunter (frontdesk) dan keluar menghantar arahan.
    // Pelawat hanya datang dari pintu (door) lalu terus ke sini.
    reception: {
        label: 'Reception Counter',
        hideLabel: true,
        spot: { c: 3, r: 14 },
        capacity: 2,
        cells: [],
        stands: [{ c: 3, r: 14, act: 'handover' }, { c: 4, r: 14, act: 'handover' }],
        queue: [{ c: 3, r: 15 }, { c: 4, r: 15 }],
    },
    frontdesk: {
        label: 'Front Desk',
        hideLabel: true,
        spot: { c: 3, r: 12 },
        cells: [],
        stands: [{ c: 3, r: 12, flip: true }, { c: 4, r: 12, flip: true }],
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
        stands: [{ c: 10, r: 6 }, { c: 9, r: 6 }, { c: 11, r: 6 }, { c: 8, r: 5 }, { c: 12, r: 5, flip: true }, { c: 8, r: 6 }, { c: 12, r: 6, flip: true }],
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

    // Bilik board meeting: meja panjang untuk mesyuarat dan briefing. 4 duduk, selebihnya berdiri.
    boardroom: {
        label: 'Board Room',
        spot: { c: 11, r: 11 },
        seats: [{ c: 10, r: 14 }, { c: 11, r: 14 }, { c: 12, r: 14 }, { c: 13, r: 14 }],
        stands: [
            { c: 11, r: 11 }, { c: 12, r: 11 }, { c: 10, r: 11 }, { c: 13, r: 11 },
            { c: 9, r: 12 }, { c: 14, r: 12, flip: true }, { c: 9, r: 13 },
            { c: 9, r: 11 }, { c: 14, r: 11, flip: true },
        ],
        cells: [
            { c: 10, r: 12, kind: 'boardtable' }, { c: 11, r: 12, kind: 'boardtable' },
            { c: 12, r: 12, kind: 'boardtable' }, { c: 13, r: 12, kind: 'boardtable' },
            { c: 10, r: 13, kind: 'boardtable' }, { c: 11, r: 13, kind: 'boardtable' },
            { c: 12, r: 13, kind: 'boardtable' }, { c: 13, r: 13, kind: 'boardtable' },
        ],
    },

    // Chill room: snooker, dart, ping-pong dan foosball. Staff yang chill berdiri main di sini.
    playroom: {
        label: 'Chill Room',
        spot: { c: 9, r: 18 },
        cells: [
            { c: 5, r: 17, kind: 'snooker' }, { c: 6, r: 17, kind: 'snooker' }, { c: 7, r: 17, kind: 'snooker' },
            { c: 5, r: 18, kind: 'snooker' }, { c: 6, r: 18, kind: 'snooker' }, { c: 7, r: 18, kind: 'snooker' },
            { c: 10, r: 17, kind: 'pong' }, { c: 11, r: 17, kind: 'pong' },
            { c: 10, r: 18, kind: 'pong' }, { c: 11, r: 18, kind: 'pong' },
            { c: 13, r: 17, kind: 'foos' }, { c: 14, r: 17, kind: 'foos' },
        ],
        stands: [
            { c: 3, r: 17, flip: true, act: 'dart' }, { c: 5, r: 16, act: 'play' }, { c: 10, r: 16, act: 'play' },
            { c: 13, r: 16, act: 'play' }, { c: 6, r: 19, act: 'play' }, { c: 10, r: 19, act: 'play' },
            { c: 3, r: 18, flip: true, act: 'dart' }, { c: 4, r: 17, act: 'play' }, { c: 9, r: 17, act: 'play' },
            { c: 14, r: 18, flip: true, act: 'play' }, { c: 7, r: 16, act: 'play' }, { c: 12, r: 18, flip: true, act: 'play' },
            { c: 3, r: 16, flip: true, act: 'dart' }, { c: 8, r: 18, flip: true, act: 'play' }, { c: 11, r: 19, act: 'play' },
            { c: 5, r: 19, act: 'play' }, { c: 4, r: 18, act: 'play' }, { c: 9, r: 18, act: 'play' },
            { c: 12, r: 17, flip: true, act: 'play' }, { c: 14, r: 16, act: 'play' }, { c: 7, r: 19, act: 'play' },
            { c: 6, r: 16, act: 'play' }, { c: 11, r: 16, act: 'play' }, { c: 13, r: 18, act: 'play' },
            { c: 15, r: 17, flip: true, act: 'play' }, { c: 8, r: 17, flip: true, act: 'play' },
        ],
    },

    // Pantry: kaunter dengan mesin kopi, peti sejuk, dan meja makan. Staff ambil minuman.
    // Maksimum 2 orang serentak (capacity). Yang ketiga dan seterusnya beratur di queue sampai ada kekosongan.
    // Setiap stand di depan satu mesin berjenama (label jadi bubble: "Starbucks", "ZUS Coffee", ...).
    pantry: {
        label: 'Pantry',
        spot: { c: 24, r: 3 },
        capacity: 2,
        cells: [
            { c: 23, r: 1, kind: 'machine_starbucks' }, { c: 24, r: 1, kind: 'machine_zus' }, { c: 25, r: 1, kind: 'icecream' },
            { c: 26, r: 1, kind: 'chiller_redbull' }, { c: 27, r: 1, kind: 'chiller_redbull' },
            { c: 24, r: 4, kind: 'table' }, { c: 25, r: 4, kind: 'table' },
        ],
        stands: [
            { c: 23, r: 2, act: 'drink', label: 'Starbucks' }, { c: 24, r: 2, act: 'drink', label: 'ZUS Coffee' },
            { c: 25, r: 2, act: 'drink', label: 'Baskin Robbins' }, { c: 26, r: 2, act: 'drink', label: 'Red Bull' },
        ],
        queue: [{ c: 24, r: 6 }, { c: 25, r: 6 }, { c: 23, r: 6 }, { c: 26, r: 6 }, { c: 24, r: 7 }, { c: 25, r: 7 }],
    },

    // Toilet: singki di belakang, kubikel di bawah. Staff berdiri sekejap.
    toilet: {
        label: 'Toilet',
        spot: { c: 24, r: 17 },
        cells: [
            { c: 23, r: 15, kind: 'sink' }, { c: 24, r: 15, kind: 'sink' }, { c: 25, r: 15, kind: 'sink' },
            { c: 23, r: 19, kind: 'wc' }, { c: 25, r: 19, kind: 'wc' }, { c: 27, r: 19, kind: 'wc' },
        ],
        stands: [
            { c: 24, r: 16 }, { c: 23, r: 18 }, { c: 25, r: 18 }, { c: 27, r: 18 }, { c: 23, r: 16 }, { c: 25, r: 16 },
        ],
    },
};

// Teks bubble lalai bila staff tiada tugas (contoh bila di bilik rehat)
export const DEPT_BUBBLE = {
    toilet: 'Toilet break',
    pantry: 'Ambil minuman',
    playroom: 'Chill',
    boardroom: 'Board briefing',
    meeting: 'Client meeting',
    coffee: 'Kopi',
    water_cooler: 'Rehat',
    reception: 'Hantar barang',
    frontdesk: 'Jaga kaunter',
};

// Dekor: hiasan yang juga disekat (kecuali yang tiada cells)
export const DECOR = [
    { kind: 'shelf', cells: [{ c: 4, r: 1 }, { c: 5, r: 1 }] },
    { kind: 'shelf', cells: [{ c: 1, r: 9 }, { c: 1, r: 10 }] },
    // Partition separuh tinggi: reception (kiri bawah), break room, dan dinding toilet (c=21)
    { kind: 'partition_a', cells: [{ c: 2, r: 11 }, { c: 3, r: 11 }, { c: 4, r: 11 }, { c: 15, r: 12 }, { c: 17, r: 12 }] },
    { kind: 'partition_a_logo', cells: [{ c: 16, r: 12 }] },
    { kind: 'partition_b', cells: [{ c: 5, r: 13 }, { c: 14, r: 13 }, { c: 14, r: 14 }, { c: 21, r: 15 }, { c: 21, r: 16 }, { c: 21, r: 17 }, { c: 21, r: 18 }, { c: 21, r: 19 }] },
    { kind: 'partition_b_logo', cells: [{ c: 5, r: 12 }] },
    { kind: 'plant', cells: [{ c: 1, r: 4 }] },
    { kind: 'plant', cells: [{ c: 21, r: 6 }] },
    { kind: 'plant', cells: [{ c: 13, r: 15 }] },
    { kind: 'plant', cells: [{ c: 1, r: 15 }] },
    { kind: 'plant', cells: [{ c: 23, r: 9 }] },
    { kind: 'plant', cells: [{ c: 27, r: 12 }] },
    { kind: 'plant', cells: [{ c: 22, r: 6 }] },
    { kind: 'server', cells: [{ c: 21, r: 9 }, { c: 21, r: 10 }] },
];

export const VENDOR_COLORS = {
    claude: 0xd97757,
    codex: 0x10a37f,
    hermes: 0x8b5cf6,
    antigravity: 0x4285f4,
    generic: 0x64748b,
};

// Gaya watak. 'default' guna fail staff_{layer}.png, yang lain staff_{gaya}_{layer}.png
export const AVATARS = ['default', 'woman', 'hiphop', 'genz', 'recep', 'grab', 'shopee', 'jnt', 'dhl'];
export const AVATAR_LABELS = {
    default: 'Lelaki biasa', woman: 'Wanita', hiphop: 'Hip-hop', genz: 'Gen Z',
    recep: 'Receptionist', grab: 'Grab Food rider', shopee: 'ShopeeFood rider', jnt: 'J&T Express', dhl: 'DHL Express',
};
// Pelawat penghantaran: datang dari pintu, tekan loceng, terus ke kaunter reception
export const VISITOR_STYLES = ['grab', 'shopee', 'jnt', 'dhl'];
// Warna uniform (tint lapisan shirt) menggantikan warna vendor bila gaya ada entri di sini
export const STYLE_SHIRT = { recep: 0x4285f4, grab: 0x00b14f, shopee: 0xee4d2d, jnt: 0xd5202a, dhl: 0xffcc00 };

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

// Tempat berdiri (briefing, bilik bermain, pantry, toilet)
export function standsFor(department) {
    return DEPARTMENTS[department]?.stands ?? [];
}

// Had orang serentak (cth. pantry = 2) dan tempat beratur bila penuh
export function capacityFor(department) {
    return DEPARTMENTS[department]?.capacity ?? null;
}

export function queueFor(department) {
    return DEPARTMENTS[department]?.queue ?? [];
}

export function allSeats() {
    return Object.keys(DEPARTMENTS).flatMap((key) => seatsFor(key));
}

export function spotFor(department) {
    return (DEPARTMENTS[department] ?? DEPARTMENTS.door).spot;
}
