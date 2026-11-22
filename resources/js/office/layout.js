// Layout bangunan 4 aras (lihat docs/multifloor-spec.md). Setiap aras guna grid 28x20 yang sama.
// Baris r=0 dan lajur c=0 ialah luar dinding (disekat). L1-L3: dinding A sepanjang r=1, B sepanjang c=1.
// Tepi hadapan (r=19, c=27) tiada dinding: teres luar di situ dipagar railing. Rooftop tiada dinding langsung.
// cells = furniture yang disekat. kind = nama fail PNG di public/assets/office (desk, table, sofa_blue, ...).
//   kind 'block' = penyekat tak nampak (enjin tak lukis), dipakai untuk air kolam renang.
// spot = tile tempat staff berdiri bila sampai ke department.
// seats = kerusi (duduk, nampak dari belakang, menghadap r-1). 'desk' dapat seat automatik di r+1;
//   training_desk / exec_desk perlu seats eksplisit.
// stands = tempat berdiri; act = aktiviti ('play' main, 'dart' lontar dart, 'drink' minum, 'handover' serah barang).
//   flip = menghadap kiri.

export const GRID = { cols: 28, rows: 20 };
export const TILE = { w: 56, h: 28 };
export const ORIGIN = { x: 600, y: 150 };
export const CANVAS = { w: 1440, h: 860 };

// Bangunan 4 aras. Setiap aras guna grid 28x20 yang sama.
export const FLOORS = [
    { id: 1, key: 'L1', label: 'Level 1', name: 'Lobi, Auditorium & Chill', walls: true },
    { id: 2, key: 'L2', label: 'Level 2', name: 'Sales, Marketing, IT & Big Pantry', walls: true },
    { id: 3, key: 'L3', label: 'Level 3', name: 'Eksekutif & Big Meeting Room', walls: true },
    { id: 4, key: 'RT', label: 'Rooftop', name: 'Kolam Renang, Taman & Party', walls: false },
];

// Tangga: kedudukan sama setiap aras. cell = sprite (disekat), landing = tile naik/turun/muncul.
export const STAIRS = { cell: { c: 26, r: 10 }, landing: { c: 25, r: 10 } };

// Pembantu data: deretan sel sepanjang c (r tetap) atau sepanjang r (c tetap)
function alongC(kind, r, cols) {
    return cols.map((c) => (kind ? { c, r, kind } : { c, r }));
}
function alongR(kind, c, rows) {
    return rows.map((r) => (kind ? { c, r, kind } : { c, r }));
}
function range(a, b, skip = []) {
    const out = [];
    for (let i = a; i <= b; i++) if (!skip.includes(i)) out.push(i);
    return out;
}
// Segi empat sel: kind (atau null) dari (c0,r0) hingga (c1,r1)
function rect(kind, c0, r0, c1, r1) {
    const out = [];
    for (let r = r0; r <= r1; r++) {
        for (let c = c0; c <= c1; c++) out.push(kind ? { c, r, kind } : { c, r });
    }
    return out;
}

// Toilet sayap kanan bawah (sama di L1 dan L2)
const TOILET_CELLS = [
    { c: 23, r: 15, kind: 'sink' }, { c: 24, r: 15, kind: 'sink' }, { c: 25, r: 15, kind: 'sink' },
    { c: 23, r: 19, kind: 'wc' }, { c: 25, r: 19, kind: 'wc' }, { c: 27, r: 19, kind: 'wc' },
];
const TOILET_STANDS = [
    { c: 24, r: 16 }, { c: 23, r: 18 }, { c: 25, r: 18 }, { c: 27, r: 18 }, { c: 23, r: 16 }, { c: 25, r: 16 },
];

// Pejabat eksekutif kaca (L3): bahagian dalam c0..c0+4, r 1..5; meja di tengah, pelawat di seberang meja
function execOffice(label, c0) {
    const c = c0 + 2;
    return {
        floor: 3,
        label,
        spot: { c: c0 + 4, r: 5 },
        cells: [{ c, r: 3, kind: 'exec_desk' }],
        seats: [{ c, r: 4 }],
        stands: [{ c: c - 1, r: 2 }, { c: c + 1, r: 2, flip: true }],
    };
}

export const DEPARTMENTS = {
    // ============================== LEVEL 1 ==============================
    // Pintu masuk (dinding B, r=14) + reception kiri bawah (kekal seperti dulu)
    door: {
        floor: 1,
        label: 'Reception',
        spot: { c: 1, r: 14 },
        cells: [{ c: 3, r: 13, kind: 'reception' }, { c: 4, r: 13, kind: 'reception' }],
    },
    // Kaunter reception: pelawat (rider/kurier) berdiri di depan kaunter (act 'handover', maksimum 2 serentak,
    // selebihnya beratur). Resepsionis berdiri di belakang kaunter (frontdesk) dan keluar menghantar arahan.
    // Pelawat hanya datang dari pintu (door) lalu terus ke sini.
    reception: {
        floor: 1,
        label: 'Reception Counter',
        hideLabel: true,
        spot: { c: 3, r: 14 },
        capacity: 2,
        cells: [],
        stands: [{ c: 3, r: 14, act: 'handover' }, { c: 4, r: 14, act: 'handover' }],
        queue: [{ c: 3, r: 15 }, { c: 4, r: 15 }],
    },
    frontdesk: {
        floor: 1,
        label: 'Front Desk',
        hideLabel: true,
        spot: { c: 3, r: 12 },
        cells: [],
        stands: [{ c: 3, r: 12, flip: true }, { c: 4, r: 12, flip: true }],
    },
    // Auditorium pelancaran (bekas Sales, belakang kiri): pentas di dinding A (DECOR 'stage' r=2, skrin r=1),
    // podium + speaker di apron r=3 (3 stand penceramah), 4 baris x 7 kerusi menghadap pentas (aisle c=5),
    // beberapa tempat berdiri di belakang (r=9).
    auditorium: {
        floor: 1,
        label: 'Launch Auditorium',
        spot: { c: 5, r: 9 },
        cells: [
            { c: 5, r: 3, kind: 'podium' },
            { c: 2, r: 3, kind: 'speaker_stack' }, { c: 8, r: 3, kind: 'speaker_stack' },
        ],
        seats: [5, 6, 7, 8].flatMap((r) => alongC(null, r, [1, 2, 3, 4, 6, 7, 8])),
        stands: [
            { c: 4, r: 3 }, { c: 6, r: 3, flip: true }, { c: 3, r: 3 },
            { c: 3, r: 9 }, { c: 4, r: 9 }, { c: 6, r: 9 }, { c: 7, r: 9 },
        ],
    },
    // Meeting room klien (anjak ke c10..12, papan putih di dinding A atasnya)
    meeting: {
        floor: 1,
        label: 'Meeting Room',
        spot: { c: 11, r: 6 },
        seats: [{ c: 10, r: 5 }, { c: 11, r: 5 }, { c: 12, r: 5 }],
        stands: [{ c: 11, r: 6 }, { c: 10, r: 6 }, { c: 12, r: 6 }, { c: 9, r: 5 }, { c: 13, r: 5, flip: true }, { c: 9, r: 6 }, { c: 13, r: 6, flip: true }],
        cells: rect('table', 10, 3, 12, 4),
    },
    // Training: bilik kaca (c15..20, r1..8, pintu di (17,9)), skrin + whiteboard di dinding A, 2 deret meja latihan (lorong tengah c=17 sejajar pintu)
    training: {
        floor: 1,
        label: 'Training Room',
        spot: { c: 17, r: 8 },
        cells: [
            { c: 15, r: 1, kind: 'whiteboard' }, { c: 17, r: 1, kind: 'projector_screen' },
            ...alongC('training_desk', 4, range(15, 20, [17])), ...alongC('training_desk', 6, range(15, 20, [17])),
        ],
        seats: [...alongC(null, 5, range(15, 20, [17])), ...alongC(null, 7, range(15, 20, [17]))],
        stands: [{ c: 17, r: 2 }, { c: 16, r: 2, flip: true }],
    },
    // Client space: tiga set sofa + coffee table (r10..12), kerusi pelanggan di depan meja, water cooler
    client: {
        floor: 1,
        label: 'Client Space',
        spot: { c: 10, r: 12 },
        cells: [
            { c: 7, r: 10, kind: 'sofa_blue' }, { c: 8, r: 10, kind: 'sofa_blue' },
            { c: 7, r: 11, kind: 'coffee_table' }, { c: 8, r: 11, kind: 'coffee_table' },
            { c: 11, r: 10, kind: 'sofa_red' }, { c: 12, r: 10, kind: 'sofa_red' },
            { c: 11, r: 11, kind: 'coffee_table' }, { c: 12, r: 11, kind: 'coffee_table' },
            { c: 15, r: 10, kind: 'sofa_green' }, { c: 16, r: 10, kind: 'sofa_green' },
            { c: 15, r: 11, kind: 'coffee_table' }, { c: 16, r: 11, kind: 'coffee_table' },
            { c: 19, r: 10, kind: 'cooler' },
        ],
        seats: [{ c: 7, r: 12 }, { c: 8, r: 12 }, { c: 11, r: 12 }, { c: 12, r: 12 }, { c: 15, r: 12 }, { c: 16, r: 12 }],
        stands: [
            { c: 6, r: 11 }, { c: 9, r: 11, flip: true }, { c: 10, r: 11 }, { c: 13, r: 11, flip: true },
            { c: 14, r: 11 }, { c: 19, r: 11, act: 'drink' },
        ],
    },
    // Chill & Game (bahagian bawah L1, r14..19): snooker, ping-pong, foosball, dart (papan di dinding B) dan
    // sudut lounge dengan sofa + coffee table. Rug checker dikongsi dengan Gaming Area (kanan bawah).
    playroom: {
        floor: 1,
        label: 'Chill Area',
        spot: { c: 9, r: 17 },
        cells: [
            ...rect('snooker', 6, 15, 8, 16),
            ...rect('pong', 11, 15, 12, 16),
            { c: 15, r: 15, kind: 'foos' }, { c: 16, r: 15, kind: 'foos' },
            { c: 6, r: 18, kind: 'sofa_blue' }, { c: 7, r: 18, kind: 'sofa_blue' },
            { c: 6, r: 19, kind: 'coffee_table' }, { c: 7, r: 19, kind: 'coffee_table' },
            { c: 10, r: 18, kind: 'sofa_yellow' }, { c: 11, r: 18, kind: 'sofa_yellow' },
            { c: 10, r: 19, kind: 'coffee_table' }, { c: 11, r: 19, kind: 'coffee_table' },
        ],
        stands: [
            // snooker
            { c: 5, r: 15, act: 'play' }, { c: 5, r: 16, act: 'play' }, { c: 9, r: 15, act: 'play', flip: true }, { c: 9, r: 16, act: 'play', flip: true },
            { c: 6, r: 14, act: 'play' }, { c: 7, r: 14, act: 'play' }, { c: 8, r: 14, act: 'play' },
            { c: 6, r: 17, act: 'play' }, { c: 7, r: 17, act: 'play' }, { c: 8, r: 17, act: 'play' },
            // ping-pong
            { c: 10, r: 15, act: 'play' }, { c: 10, r: 16, act: 'play' }, { c: 13, r: 15, act: 'play', flip: true }, { c: 13, r: 16, act: 'play', flip: true },
            { c: 11, r: 14, act: 'play' }, { c: 12, r: 14, act: 'play' }, { c: 11, r: 17, act: 'play' }, { c: 12, r: 17, act: 'play' },
            // foosball
            { c: 14, r: 15, act: 'play' }, { c: 17, r: 15, act: 'play', flip: true },
            { c: 15, r: 14, act: 'play' }, { c: 16, r: 14, act: 'play' }, { c: 15, r: 16, act: 'play' }, { c: 16, r: 16, act: 'play' },
            // dart (papan di dinding B)
            { c: 3, r: 16, flip: true, act: 'dart' }, { c: 3, r: 17, flip: true, act: 'dart' }, { c: 3, r: 18, flip: true, act: 'dart' },
            // lounge
            { c: 5, r: 18 }, { c: 5, r: 19 }, { c: 8, r: 18, flip: true }, { c: 9, r: 18 },
            { c: 8, r: 19, flip: true }, { c: 9, r: 19 }, { c: 12, r: 18, flip: true }, { c: 12, r: 19, flip: true },
        ],
    },
    // Gaming (kanan bawah L1): 4 arcade, TV console + beanbag
    gaming: {
        floor: 1,
        label: 'Gaming Area',
        spot: { c: 17, r: 17 },
        cells: [
            ...alongC('arcade', 18, [13, 14, 15, 16]),
            { c: 18, r: 15, kind: 'tv_console' }, { c: 19, r: 15, kind: 'tv_console' },
            { c: 17, r: 16, kind: 'beanbag_red' }, { c: 20, r: 16, kind: 'beanbag_blue' },
            { c: 17, r: 18, kind: 'beanbag_green' }, { c: 20, r: 18, kind: 'beanbag_yellow' },
        ],
        stands: [
            { c: 18, r: 16, act: 'play' }, { c: 19, r: 16, act: 'play', flip: true },
            { c: 18, r: 17, act: 'play' }, { c: 19, r: 17, act: 'play', flip: true },
            { c: 13, r: 19, act: 'play' }, { c: 14, r: 19, act: 'play' }, { c: 15, r: 19, act: 'play' }, { c: 16, r: 19, act: 'play' },
        ],
    },
    // Pantry berjenama: maksimum 2 orang serentak (capacity), yang lain beratur di queue.
    // Setiap stand di depan satu mesin berjenama (label jadi bubble: "Starbucks", "ZUS Coffee", ...).
    pantry: {
        floor: 1,
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
        floor: 1,
        label: 'Toilet',
        spot: { c: 24, r: 17 },
        cells: TOILET_CELLS,
        stands: TOILET_STANDS,
    },

    // ============================== LEVEL 2 ==============================
    // Marketing: dua deret meja di kiri atas, papan kanban (cork board dinding B) di sebelahnya
    marketing: {
        floor: 2,
        label: 'Marketing Department',
        spot: { c: 5, r: 5 },
        cells: [...alongC('desk', 3, [2, 3, 4, 6, 7, 8]), ...alongC('desk', 6, [2, 3, 4, 6, 7, 8])],
    },
    kanban: {
        floor: 2,
        label: 'Marketing Plan',
        hideLabel: true,
        spot: { c: 1, r: 6 },
        cells: [],
        stands: [{ c: 1, r: 5, flip: true }, { c: 1, r: 7, flip: true }],
    },
    // IT Department: enam kluster meja (c 10..19, r 3..7), rak server di c=21
    frontend: {
        floor: 2,
        label: 'IT · Frontend',
        spot: { c: 11, r: 5 },
        cells: alongC('desk', 3, [10, 11, 12]),
    },
    backend: {
        floor: 2,
        label: 'IT · Backend',
        spot: { c: 15, r: 5 },
        cells: alongC('desk', 3, [14, 15, 16]),
    },
    qa: {
        floor: 2,
        label: 'IT · QA',
        spot: { c: 19, r: 5 },
        cells: alongC('desk', 3, [18, 19]),
    },
    research: {
        floor: 2,
        label: 'IT · Research',
        spot: { c: 11, r: 8 },
        cells: alongC('desk', 6, [10, 11, 12]),
    },
    deploy: {
        floor: 2,
        label: 'IT · DevOps',
        spot: { c: 15, r: 8 },
        cells: alongC('desk', 6, [14, 15, 16]),
    },
    ops: {
        floor: 2,
        label: 'IT · Ops',
        spot: { c: 19, r: 8 },
        cells: alongC('desk', 6, [18, 19]),
    },
    // Sales (bekas big meeting room): 12 meja dalam dua deret (r10, r13), seat auto di r+1
    sales: {
        floor: 2,
        label: 'Sales Department',
        spot: { c: 14, r: 12 },
        cells: [...alongC('desk', 10, [11, 12, 13, 16, 17, 18]), ...alongC('desk', 13, [11, 12, 13, 16, 17, 18])],
    },
    // Head of Department: bilik kaca c 1..6 r 11..14, pintu di (7,12), loceng approval di luar pintu
    head_office: {
        floor: 2,
        label: 'Head of Department',
        spot: { c: 6, r: 12 },
        cells: [{ c: 3, r: 12, kind: 'exec_desk' }],
        seats: [{ c: 3, r: 13 }],
        stands: [{ c: 2, r: 11 }, { c: 4, r: 11, flip: true }],
    },
    approval: {
        floor: 2,
        label: 'Approval',
        hideLabel: true,
        spot: { c: 8, r: 12 },
        cells: [{ c: 8, r: 11, kind: 'bell' }],
    },
    // Big Pantry (sayap kanan atas): mesin kopi, kaunter, peti sejuk; lounge dengan SATU meja di sebelah sofa dan cooler
    coffee: {
        floor: 2,
        label: 'Big Pantry · Coffee',
        spot: { c: 25, r: 3 },
        cells: [
            { c: 23, r: 1, kind: 'machine' }, { c: 24, r: 1, kind: 'machine' },
            { c: 25, r: 1, kind: 'pantry_counter' }, { c: 26, r: 1, kind: 'pantry_counter' }, { c: 27, r: 1, kind: 'fridge' },
        ],
        stands: [
            { c: 23, r: 2, act: 'drink' }, { c: 24, r: 2, act: 'drink' }, { c: 26, r: 2 }, { c: 27, r: 2, act: 'drink' },
        ],
    },
    water_cooler: {
        floor: 2,
        label: 'Big Pantry · Lounge',
        spot: { c: 24, r: 7 },
        cells: [
            { c: 23, r: 5, kind: 'table' }, { c: 24, r: 5, kind: 'table' }, { c: 25, r: 5, kind: 'table' },
            { c: 27, r: 4, kind: 'sofa_yellow' }, { c: 27, r: 5, kind: 'sofa_yellow' },
            { c: 27, r: 7, kind: 'cooler' },
        ],
        seats: [{ c: 23, r: 6 }, { c: 24, r: 6 }, { c: 25, r: 6 }],
        stands: [{ c: 26, r: 4 }, { c: 26, r: 5 }, { c: 26, r: 7, act: 'drink' }, { c: 22, r: 5 }],
    },
    toilet_2: {
        floor: 2,
        label: 'Toilet L2',
        spot: { c: 24, r: 17 },
        cells: TOILET_CELLS,
        stands: TOILET_STANDS,
    },
    // Teres luar (r 16..18), dinding kaca r=15 dengan bukaan di c 8..9, pagar kaca r=19
    outdoor_chill: {
        floor: 2,
        label: 'Outdoor Chill',
        spot: { c: 8, r: 17 },
        cells: [
            { c: 11, r: 17, kind: 'umbrella_table' }, { c: 4, r: 17, kind: 'umbrella_table' },
            { c: 14, r: 17, kind: 'lounger' }, { c: 16, r: 17, kind: 'lounger' }, { c: 18, r: 17, kind: 'lounger' },
            { c: 20, r: 17, kind: 'beanbag_yellow' },
        ],
        stands: [
            { c: 10, r: 17 }, { c: 12, r: 17, flip: true }, { c: 11, r: 16 }, { c: 11, r: 18, flip: true },
            { c: 3, r: 17 }, { c: 5, r: 17, flip: true }, { c: 4, r: 18 },
            { c: 15, r: 17, flip: true }, { c: 17, r: 17, flip: true }, { c: 19, r: 17, act: 'drink' },
        ],
    },

    // ============================== LEVEL 3 ==============================
    // Empat pejabat kaca sepanjang dinding A (c 1..23, r 1..5); pintu di (c0+4, 6)
    ceo: execOffice('CEO Office', 1),
    cfo: execOffice('CFO Office', 7),
    md: execOffice('MD Office', 13),
    hod: execOffice('HOD Office', 19),
    // Big Meeting Room (tengah L3): meja panjang 9x2 (r11..12), 9 duduk (r13) + 26 berdiri = 35 orang.
    // Projektor + whiteboard di r=9 menghadap meja, stand presenter di r=10.
    boardroom: {
        floor: 3,
        label: 'Big Meeting Room',
        spot: { c: 13, r: 10 },
        cells: [
            ...alongC('boardtable', 11, range(9, 17)), ...alongC('boardtable', 12, range(9, 17)),
            { c: 11, r: 9, kind: 'whiteboard' }, { c: 13, r: 9, kind: 'projector_screen' }, { c: 15, r: 9, kind: 'whiteboard' },
        ],
        seats: alongC(null, 13, range(9, 17)),
        stands: [
            ...range(8, 18).map((c) => (c > 13 ? { c, r: 10, flip: true } : { c, r: 10 })),
            { c: 8, r: 11 }, { c: 8, r: 12 }, { c: 8, r: 13 },
            { c: 18, r: 11, flip: true }, { c: 18, r: 12, flip: true }, { c: 18, r: 13, flip: true },
            ...alongC(null, 15, range(9, 17)),
        ],
    },

    // ============================== ROOFTOP ==============================
    // Taman + party (kolam di tengah, taman kiri, BBQ/bar/DJ atas, umbrella kanan bawah)
    rooftop: {
        floor: 4,
        label: 'Garden & Party',
        spot: { c: 21, r: 10 },
        cells: [
            // BBQ, bar, DJ
            { c: 12, r: 3, kind: 'bbq' }, { c: 13, r: 3, kind: 'bbq' },
            { c: 16, r: 3, kind: 'bar_counter' }, { c: 17, r: 3, kind: 'bar_counter' }, { c: 18, r: 3, kind: 'bar_counter' },
            { c: 22, r: 4, kind: 'dj_booth' },
            // belon dan meja party
            { c: 10, r: 3, kind: 'balloons' }, { c: 15, r: 3, kind: 'balloons' }, { c: 20, r: 3, kind: 'balloons' }, { c: 22, r: 2, kind: 'balloons' },
            { c: 20, r: 7, kind: 'party_table' }, { c: 25, r: 7, kind: 'party_table' },
            // umbrella kanan bawah
            { c: 21, r: 14, kind: 'umbrella_table' }, { c: 24, r: 14, kind: 'umbrella_table' },
            { c: 20, r: 17, kind: 'lounger' }, { c: 22, r: 17, kind: 'lounger' }, { c: 24, r: 17, kind: 'lounger' },
        ],
        stands: [
            // taman: sekeliling air pancut, jalan-jalan
            { c: 5, r: 10 }, { c: 4, r: 11 }, { c: 6, r: 11, flip: true }, { c: 5, r: 12 },
            { c: 3, r: 9 }, { c: 7, r: 9, flip: true }, { c: 3, r: 13 }, { c: 7, r: 13, flip: true },
            { c: 5, r: 8 }, { c: 5, r: 14 }, { c: 4, r: 16 }, { c: 6, r: 16, flip: true },
            // BBQ dan bar
            { c: 12, r: 4, act: 'drink' }, { c: 13, r: 4, act: 'drink', flip: true },
            { c: 11, r: 3, act: 'drink' }, { c: 14, r: 3, act: 'drink', flip: true },
            { c: 16, r: 4, act: 'drink' }, { c: 17, r: 4, act: 'drink' }, { c: 18, r: 4, act: 'drink', flip: true },
            // lantai tari depan DJ
            { c: 21, r: 5 }, { c: 22, r: 5 }, { c: 23, r: 5, flip: true },
            { c: 21, r: 6 }, { c: 23, r: 6, flip: true }, { c: 22, r: 7 },
            // umbrella kanan bawah
            { c: 20, r: 14 }, { c: 22, r: 14, flip: true }, { c: 23, r: 14, act: 'drink' }, { c: 25, r: 14, flip: true },
        ],
    },
    // Kolam renang 9x4 (c10..18, r9..12): air disekat (DECOR 'block'), staff berdiri di tebing dan kerusi rehat
    pool: {
        floor: 4,
        label: 'Swimming Pool',
        spot: { c: 14, r: 13 },
        cells: [
            { c: 10, r: 14, kind: 'lounger' }, { c: 12, r: 14, kind: 'lounger' }, { c: 14, r: 14, kind: 'umbrella_table' },
            { c: 16, r: 14, kind: 'lounger' }, { c: 18, r: 14, kind: 'lounger' },
            { c: 11, r: 16, kind: 'lounger' }, { c: 13, r: 16, kind: 'lounger' }, { c: 15, r: 16, kind: 'lounger' }, { c: 17, r: 16, kind: 'lounger' },
        ],
        stands: [
            // tebing atas (papan lompat di c=14)
            { c: 10, r: 8 }, { c: 11, r: 8 }, { c: 12, r: 8 }, { c: 16, r: 8, flip: true }, { c: 17, r: 8, flip: true }, { c: 18, r: 8, flip: true },
            // tebing kiri dan kanan (tangga di (19,11))
            { c: 9, r: 9 }, { c: 9, r: 10 }, { c: 9, r: 11 }, { c: 9, r: 12 },
            { c: 19, r: 9, flip: true }, { c: 19, r: 10, flip: true }, { c: 19, r: 12, flip: true },
            // tebing bawah dan sekitar kerusi rehat
            { c: 10, r: 13 }, { c: 12, r: 13, act: 'drink' }, { c: 14, r: 13 }, { c: 16, r: 13, act: 'drink' }, { c: 18, r: 13 },
            { c: 13, r: 14, act: 'drink' }, { c: 15, r: 14, act: 'drink', flip: true },
            { c: 11, r: 17 }, { c: 13, r: 17, act: 'drink' }, { c: 15, r: 17 }, { c: 17, r: 17, flip: true },
        ],
    },
};

// Teks bubble lalai bila staff tiada tugas (contoh bila di bilik rehat)
export const DEPT_BUBBLE = {
    toilet: 'Toilet break',
    toilet_2: 'Toilet break',
    pantry: 'Ambil minuman',
    playroom: 'Chill',
    gaming: 'Main game',
    boardroom: 'Big briefing',
    meeting: 'Client meeting',
    auditorium: 'Launch event',
    coffee: 'Kopi',
    water_cooler: 'Rehat',
    reception: 'Hantar barang',
    frontdesk: 'Jaga kaunter',
    training: 'Training',
    sales: 'Call client',
    client: 'Layan client',
    marketing: 'Campaign',
    kanban: 'Plan campaign',
    head_office: 'Review',
    approval: 'Minta approval',
    outdoor_chill: 'Ambil angin',
    ceo: 'Strategy',
    cfo: 'Budget review',
    md: 'Board prep',
    hod: 'Team review',
    rooftop: 'Taman & party',
    pool: 'Berenang',
};

// Kolam renang: air c10..18, r9..12 (disekat)
const POOL = { c0: 10, r0: 9, c1: 18, r1: 12 };

// Dekor: hiasan yang juga disekat. floor wajib.
export const DECOR = [
    // ----- L1 -----
    { floor: 1, kind: 'shelf', cells: [{ c: 1, r: 9 }, { c: 1, r: 10 }] },
    // Pentas auditorium (c2..8, r=2) dengan skrin LED di dinding belakang (r=1)
    { floor: 1, kind: 'stage', cells: alongC(null, 2, range(2, 8)) },
    { floor: 1, kind: 'stage_screen', cells: alongC(null, 1, [4, 5, 6]) },
    // Bilik kaca training: c14 dan c21 (r1..8), depan r=9 dengan pintu di c=17
    { floor: 1, kind: 'glass_b', cells: [14, 21].flatMap((c) => alongR(null, c, range(1, 8))) },
    { floor: 1, kind: 'glass_a', cells: alongC(null, 9, range(14, 21, [17])) },
    // Partition separuh tinggi: reception (kiri bawah) dan dinding toilet (c=21)
    { floor: 1, kind: 'partition_a', cells: [{ c: 2, r: 11 }, { c: 3, r: 11 }, { c: 4, r: 11 }] },
    { floor: 1, kind: 'partition_b', cells: [{ c: 5, r: 13 }, ...alongR(null, 21, range(15, 19))] },
    { floor: 1, kind: 'partition_b_logo', cells: [{ c: 5, r: 12 }] },
    {
        floor: 1,
        kind: 'plant',
        cells: [
            { c: 9, r: 2 }, { c: 22, r: 6 }, { c: 1, r: 15 }, { c: 23, r: 9 }, { c: 27, r: 12 },
            { c: 6, r: 12 }, { c: 14, r: 10 }, { c: 2, r: 19 }, { c: 20, r: 19 },
        ],
    },

    // ----- L2 -----
    { floor: 2, kind: 'server', cells: [{ c: 21, r: 2 }, { c: 21, r: 3 }] },
    { floor: 2, kind: 'shelf', cells: [{ c: 1, r: 13 }, { c: 1, r: 14 }] },
    { floor: 2, kind: 'partition_b', cells: alongR(null, 21, range(15, 19)) },
    // Bilik kaca Head of Department (pintu di (7,12))
    { floor: 2, kind: 'glass_a', cells: alongC(null, 10, range(1, 6)) },
    { floor: 2, kind: 'glass_b', cells: [{ c: 7, r: 10 }, { c: 7, r: 11 }, { c: 7, r: 13 }, { c: 7, r: 14 }] },
    // Dinding kaca teres (r=15, bukaan c 8..9) dan pagar tepi hadapan (r=19)
    { floor: 2, kind: 'glass_a', cells: alongC(null, 15, range(1, 20, [8, 9])) },
    { floor: 2, kind: 'railing_a', cells: alongC(null, 19, range(1, 20)) },
    { floor: 2, kind: 'planter', cells: [{ c: 1, r: 17 }, { c: 7, r: 18 }, { c: 20, r: 16 }] },
    { floor: 2, kind: 'plant', cells: [{ c: 1, r: 2 }, { c: 21, r: 7 }, { c: 6, r: 14 }, { c: 9, r: 9 }, { c: 22, r: 9 }, { c: 27, r: 12 }, { c: 20, r: 13 }] },

    // ----- L3 -----
    // Pejabat kaca: dinding sisi c=6,12,18,24 (r 1..5), depan r=6 dengan pintu di c 5, 11, 17, 23
    { floor: 3, kind: 'glass_b', cells: [6, 12, 18, 24].flatMap((c) => alongR(null, c, range(1, 5))) },
    { floor: 3, kind: 'glass_a', cells: alongC(null, 6, range(1, 24, [5, 11, 17, 23])) },
    { floor: 3, kind: 'shelf', cells: [{ c: 1, r: 1 }, { c: 7, r: 1 }, { c: 13, r: 1 }, { c: 19, r: 1 }] },
    // Lounge eksekutif: kiri tengah, kanan atas, kiri bawah dan kanan bawah
    { floor: 3, kind: 'sofa_blue', cells: [{ c: 1, r: 10 }, { c: 1, r: 11 }] },
    { floor: 3, kind: 'coffee_table', cells: [{ c: 2, r: 10 }, { c: 2, r: 11 }] },
    { floor: 3, kind: 'sofa_red', cells: [{ c: 27, r: 4 }, { c: 27, r: 5 }] },
    { floor: 3, kind: 'coffee_table', cells: [{ c: 26, r: 4 }, { c: 26, r: 5 }] },
    { floor: 3, kind: 'sofa_green', cells: [{ c: 3, r: 17 }, { c: 4, r: 17 }] },
    { floor: 3, kind: 'coffee_table', cells: [{ c: 3, r: 18 }, { c: 4, r: 18 }] },
    { floor: 3, kind: 'sofa_yellow', cells: [{ c: 22, r: 17 }, { c: 23, r: 17 }] },
    { floor: 3, kind: 'coffee_table', cells: [{ c: 22, r: 18 }, { c: 23, r: 18 }] },
    {
        floor: 3,
        kind: 'plant',
        cells: [
            { c: 5, r: 1 }, { c: 11, r: 1 }, { c: 17, r: 1 }, { c: 23, r: 1 }, { c: 25, r: 1 },
            { c: 1, r: 14 }, { c: 6, r: 9 }, { c: 19, r: 9 }, { c: 7, r: 16 }, { c: 19, r: 16 },
            { c: 2, r: 19 }, { c: 26, r: 18 }, { c: 25, r: 16 },
        ],
    },

    // ----- Rooftop -----
    // Pagar kaca di keempat-empat tepi (tepi belakang pada r=1 / c=1)
    { floor: 4, kind: 'railing_a', cells: [...alongC(null, 1, range(1, 27)), ...alongC(null, 19, range(1, 27))] },
    { floor: 4, kind: 'railing_b', cells: [...alongR(null, 1, range(2, 18)), ...alongR(null, 27, range(2, 18))] },
    { floor: 4, kind: 'ac_unit', cells: [{ c: 2, r: 2 }, { c: 3, r: 2 }, { c: 4, r: 2 }, { c: 2, r: 3 }, { c: 24, r: 2 }, { c: 25, r: 2 }] },
    // Air kolam: penyekat tak nampak (sprite air dilukis oleh ZONES tile 'water'), tangga dan papan lompat di tebing
    { floor: 4, kind: 'block', cells: rect(null, POOL.c0, POOL.r0, POOL.c1, POOL.r1) },
    { floor: 4, kind: 'pool_ladder', cells: [{ c: 19, r: 11 }] },
    { floor: 4, kind: 'diving_board', cells: [{ c: 14, r: 8 }] },
    // Taman
    { floor: 4, kind: 'garden_tree', cells: [{ c: 3, r: 6 }, { c: 7, r: 6 }, { c: 3, r: 16 }, { c: 7, r: 16 }] },
    { floor: 4, kind: 'fountain', cells: [{ c: 5, r: 11 }] },
    {
        floor: 4,
        kind: 'flower_bed',
        cells: [
            { c: 4, r: 10 }, { c: 6, r: 10 }, { c: 4, r: 12 }, { c: 6, r: 12 },
            { c: 3, r: 18 }, { c: 4, r: 18 }, { c: 6, r: 18 }, { c: 7, r: 18 },
        ],
    },
    { floor: 4, kind: 'planter', cells: [{ c: 2, r: 8 }, { c: 8, r: 8 }, { c: 2, r: 14 }, { c: 8, r: 14 }, { c: 20, r: 12 }, { c: 26, r: 12 }] },
    // Speaker DJ
    { floor: 4, kind: 'speaker_stack', cells: [{ c: 21, r: 4 }, { c: 23, r: 4 }] },
    {
        floor: 4,
        kind: 'plant',
        cells: [
            { c: 6, r: 2 }, { c: 9, r: 2 }, { c: 2, r: 18 }, { c: 9, r: 18 }, { c: 19, r: 18 },
            { c: 26, r: 2 }, { c: 26, r: 14 }, { c: 26, r: 18 },
        ],
    },
];

export const VENDOR_COLORS = {
    claude: 0xd97757,
    codex: 0x10a37f,
    hermes: 0x8b5cf6,
    antigravity: 0x4285f4,
    generic: 0x64748b,
};

// Gaya watak. 'default' guna fail staff_{layer}.png, yang lain staff_{gaya}_{layer}.png
export const AVATARS = ['default', 'woman', 'hiphop', 'genz', 'recep', 'grab', 'shopee', 'jnt', 'dhl', 'exec', 'exec_w'];
export const AVATAR_LABELS = {
    default: 'Lelaki biasa', woman: 'Wanita', hiphop: 'Hip-hop', genz: 'Gen Z',
    recep: 'Receptionist', grab: 'Grab Food rider', shopee: 'ShopeeFood rider', jnt: 'J&T Express', dhl: 'DHL Express',
    exec: 'Eksekutif', exec_w: 'Eksekutif (wanita)',
};
// Pelawat penghantaran: datang dari pintu, tekan loceng, terus ke kaunter reception
export const VISITOR_STYLES = ['grab', 'shopee', 'jnt', 'dhl'];
// Warna uniform (tint lapisan shirt) menggantikan warna vendor bila gaya ada entri di sini
export const STYLE_SHIRT = { recep: 0x4285f4, grab: 0x00b14f, shopee: 0xee4d2d, jnt: 0xd5202a, dhl: 0xffcc00, exec: 0x1f2a44, exec_w: 0x3b2a4a };

// Warna permaidani (sama dengan C.rug* di OfficeScene)
const RUG = { red: 0xea4335, blue: 0x4285f4, yellow: 0xfbbc05, green: 0x34a853, tiles: 0x9ad0f5, purple: 0x8b5cf6 };

// Permaidani checker kuning/hijau (zon 1x1 bergilir)
function checker(floor, c0, r0, c1, r1, colorA, colorB, alpha) {
    const out = [];
    for (let r = r0; r <= r1; r++) {
        for (let c = c0; c <= c1; c++) out.push({ floor, c0: c, r0: r, c1: c, r1: r, color: (c + r) % 2 ? colorA : colorB, alpha });
    }
    return out;
}

// Kawasan lantai, dilukis mengikut susunan (zon kemudian di atas zon awal).
// tile: 'deck' | 'grass' | 'carpet' | 'water' gantikan lantai kayu; color/alpha = tint permaidani.
export const ZONES = [
    // ----- L1 -----
    { floor: 1, c0: 1, r0: 2, c1: 9, r1: 9, tile: 'carpet' },                         // auditorium
    { floor: 1, c0: 9, r0: 5, c1: 13, r1: 7, color: RUG.red, alpha: 0.16 },            // meeting
    { floor: 1, c0: 15, r0: 1, c1: 20, r1: 8, tile: 'carpet' },                        // training (bilik kaca)
    { floor: 1, c0: 6, r0: 10, c1: 20, r1: 12, color: RUG.blue, alpha: 0.14 },         // client space
    ...checker(1, 6, 14, 20, 19, RUG.yellow, RUG.green, 0.16),                         // chill & game (kongsi)
    ...checker(1, 2, 16, 5, 19, RUG.yellow, RUG.green, 0.16),
    { floor: 1, c0: 22, r0: 15, c1: 27, r1: 19, color: RUG.tiles, alpha: 0.28 },       // toilet
    { floor: 1, c0: 23, r0: 1, c1: 27, r1: 5, color: RUG.yellow, alpha: 0.1 },         // pantry

    // ----- L2 -----
    { floor: 2, c0: 1, r0: 2, c1: 8, r1: 8, color: RUG.red, alpha: 0.08 },             // marketing
    { floor: 2, c0: 10, r0: 2, c1: 20, r1: 8, color: RUG.green, alpha: 0.08 },         // IT
    { floor: 2, c0: 10, r0: 9, c1: 20, r1: 14, color: RUG.yellow, alpha: 0.08 },       // sales
    { floor: 2, c0: 22, r0: 1, c1: 27, r1: 8, color: RUG.yellow, alpha: 0.1 },         // big pantry
    { floor: 2, c0: 22, r0: 15, c1: 27, r1: 19, color: RUG.tiles, alpha: 0.28 },       // toilet L2
    { floor: 2, c0: 1, r0: 11, c1: 6, r1: 14, tile: 'carpet' },                        // Head of Department
    { floor: 2, c0: 1, r0: 16, c1: 20, r1: 19, tile: 'deck' },                         // teres
    { floor: 2, c0: 1, r0: 16, c1: 2, r1: 18, tile: 'grass' },
    { floor: 2, c0: 6, r0: 18, c1: 8, r1: 18, tile: 'grass' },

    // ----- L3 -----
    { floor: 3, c0: 1, r0: 1, c1: 5, r1: 5, tile: 'carpet' },                          // CEO
    { floor: 3, c0: 7, r0: 1, c1: 11, r1: 5, tile: 'carpet' },                         // CFO
    { floor: 3, c0: 13, r0: 1, c1: 17, r1: 5, tile: 'carpet' },                        // MD
    { floor: 3, c0: 19, r0: 1, c1: 23, r1: 5, tile: 'carpet' },                        // HOD
    { floor: 3, c0: 8, r0: 9, c1: 18, r1: 15, tile: 'carpet' },                        // Big Meeting Room

    // ----- Rooftop -----
    { floor: 4, c0: 1, r0: 1, c1: 27, r1: 19, tile: 'deck' },
    { floor: 4, c0: 2, r0: 5, c1: 8, r1: 18, tile: 'grass' },                          // taman
    { floor: 4, c0: POOL.c0, r0: POOL.r0, c1: POOL.c1, r1: POOL.r1, tile: 'water' },   // kolam renang
];

// Sprite dinding: A (origin kiri-atas) / B (origin kanan-atas) pada kedudukan u, ketinggian atas vTop.
// Rooftop tiada dinding, jadi tiada entri.
export const WALL_DECOR = [
    // ----- L1 -----
    { floor: 1, key: 'wall_banner_a', wall: 'A', u: 3.5, vTop: 108 },     // banner launch di atas pentas
    { floor: 1, key: 'wall_window_a', wall: 'A', u: 18, vTop: 106 },
    { floor: 1, key: 'wall_window_a', wall: 'A', u: 24, vTop: 106 },
    { floor: 1, key: 'wall_window_b', wall: 'B', u: 2, vTop: 106 },
    { floor: 1, key: 'wall_window_b', wall: 'B', u: 10.4, vTop: 106 },
    { floor: 1, key: 'wall_board_a', wall: 'A', u: 10, vTop: 100 },      // atas meja meeting
    { floor: 1, key: 'wall_poster_a2', wall: 'A', u: 20.5, vTop: 102 },
    { floor: 1, key: 'wall_poster_b', wall: 'B', u: 7, vTop: 102 },
    { floor: 1, key: 'wall_door_b', wall: 'B', u: 13.5, vTop: 100 },    // pintu masuk (r=14)
    { floor: 1, key: 'wall_dartboard_b', wall: 'B', u: 17.2, vTop: 86 }, // papan dart chill & game

    // ----- L2 -----
    { floor: 2, key: 'wall_window_a', wall: 'A', u: 2, vTop: 106 },
    { floor: 2, key: 'wall_window_a', wall: 'A', u: 6, vTop: 106 },
    { floor: 2, key: 'wall_board_a', wall: 'A', u: 10, vTop: 100 },     // papan stand-up IT
    { floor: 2, key: 'wall_poster_a1', wall: 'A', u: 13.4, vTop: 102 },
    { floor: 2, key: 'wall_window_a', wall: 'A', u: 17.6, vTop: 106 },
    { floor: 2, key: 'wall_poster_a2', wall: 'A', u: 20.5, vTop: 102 },
    { floor: 2, key: 'wall_window_a', wall: 'A', u: 24, vTop: 106 },
    { floor: 2, key: 'wall_window_b', wall: 'B', u: 2, vTop: 106 },
    { floor: 2, key: 'wall_cork_b', wall: 'B', u: 5.5, vTop: 96 },      // marketing plan (kanban)
    { floor: 2, key: 'wall_window_b', wall: 'B', u: 11, vTop: 106 },    // bilik Head of Department
    { floor: 2, key: 'wall_poster_b', wall: 'B', u: 13.4, vTop: 102 },
    { floor: 2, key: 'wall_window_b', wall: 'B', u: 17.4, vTop: 106 },  // teres

    // ----- L3 -----
    { floor: 3, key: 'wall_window_a', wall: 'A', u: 2.6, vTop: 106 },   // CEO
    { floor: 3, key: 'wall_window_a', wall: 'A', u: 8.6, vTop: 106 },   // CFO
    { floor: 3, key: 'wall_window_a', wall: 'A', u: 14.6, vTop: 106 },  // MD
    { floor: 3, key: 'wall_window_a', wall: 'A', u: 20.6, vTop: 106 },  // HOD
    { floor: 3, key: 'wall_poster_a1', wall: 'A', u: 25.4, vTop: 102 },
    { floor: 3, key: 'wall_logo_b', wall: 'B', u: 2.2, vTop: 100 },     // logo dalam pejabat CEO
    { floor: 3, key: 'wall_window_b', wall: 'B', u: 8, vTop: 106 },
    { floor: 3, key: 'wall_poster_b', wall: 'B', u: 12.6, vTop: 102 },
];

// Kesan ambien: steam (mesin kopi), bubbles (water cooler), pong (bola atas meja ping-pong; c,r = pusat meja)
export const FLOOR_FX = [
    { floor: 1, kind: 'steam', c: 24, r: 1 },
    { floor: 1, kind: 'bubbles', c: 19, r: 10 },
    { floor: 1, kind: 'pong', c: 11.5, r: 15.5 },
    { floor: 2, kind: 'steam', c: 23, r: 1 },
    { floor: 2, kind: 'steam', c: 24, r: 1 },
    { floor: 2, kind: 'bubbles', c: 27, r: 7 },
];

export function floorOf(department) {
    return DEPARTMENTS[department]?.floor ?? 1;
}

export function departmentsOn(floor) {
    return Object.keys(DEPARTMENTS).filter((key) => floorOf(key) === floor);
}

// Semua tile yang disekat pada satu aras: luar dinding, furniture, dekor dan tangga
export function blockedTiles(floor = 1) {
    const set = new Set();

    for (let c = 0; c < GRID.cols; c++) set.add(`${c},0`);
    for (let r = 0; r < GRID.rows; r++) set.add(`0,${r}`);
    set.add(`${STAIRS.cell.c},${STAIRS.cell.r}`);

    for (const key of departmentsOn(floor)) {
        for (const cell of DEPARTMENTS[key].cells) {
            set.add(`${cell.c},${cell.r}`);
        }
    }
    for (const item of DECOR) {
        if ((item.floor ?? 1) !== floor) continue;
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

export function allSeats(floor = 1) {
    return departmentsOn(floor).flatMap((key) => seatsFor(key).map((seat) => ({ ...seat, dept: key })));
}

export function spotFor(department) {
    return (DEPARTMENTS[department] ?? DEPARTMENTS.door).spot;
}
