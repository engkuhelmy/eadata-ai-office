# Bangunan 4 aras: kontrak antara modul

Spec ini dikongsi oleh empat bahagian kerja: sprite, backend/demo, pelan lantai (`layout.js`) dan enjin/UI.
Ikut nama dan bentuk data di sini dengan tepat.

## Aras

| id | Tab | Isi |
|----|-----|-----|
| 1 | L1 | Pintu masuk + reception, Launch Auditorium (pentas, skrin, 28 kerusi), meeting room (client), training room (bilik kaca), client space, Chill & Game zone (snooker, ping-pong, foosball, dart, lounge, arcade, TV console + beanbag), toilet, pantry berjenama (maks 2 orang), tangga |
| 2 | L2 | Sales department (12 meja), Marketing department, Head of Department office, IT department, big pantry, toilet, outdoor chill (teres), tangga |
| 3 | L3 | Pejabat CEO, CFO, MD, HOD (Heads of Department) + Big Meeting Room (meja 9x2, 35 tempat) + lounge eksekutif, tangga |
| 4 | Rooftop | Kolam renang (air 9x4), taman (rumput, pokok, air pancut), kawasan party (BBQ, bar, DJ), payung, kerusi rehat, unit aircond, pondok tangga. Tiada dinding, pagar kaca di semua tepi |

Nama tab: L1 'Lobi, Auditorium & Chill', L2 'Sales, Marketing, IT & Big Pantry', L3 'Eksekutif & Big Meeting Room',
Rooftop 'Kolam Renang, Taman & Party'.

Setiap aras guna grid sama 28 x 20 (c 0..27, r 0..19). Baris r=0 dan lajur c=0 ialah luar dinding (disekat).
L1-L3 ada dinding belakang A (sepanjang r=1) dan B (sepanjang c=1) seperti sekarang. Rooftop: `walls: false`.
Hanya L1 ada pintu masuk (`wall_door_b` pada dinding B, reception kekal kiri bawah).

## Tangga

`STAIRS = { cell: { c: 26, r: 10 }, landing: { c: 25, r: 10 } }`, sama kedudukan di setiap aras.
`cell` ialah sprite (disekat): `stairs` di L1-L3, `stair_hut` di Rooftop.
`landing` ialah tile tempat staff berdiri sebelum naik/turun, dan tempat staff muncul bila sampai dari aras lain.
Tile `landing` mesti sentiasa kosong (tak disekat) dan boleh dicapai dari semua bilik di aras itu.

## Department (kunci global, setiap satu ada `floor`)

Kunci lama dikekalkan (backend `DepartmentRouter`, hooks dan sweep guna kunci ini). Kunci baharu bertanda *.

| Aras | Kunci | Label | Nota |
|------|-------|-------|------|
| 1 | `door` | Reception | Pintu masuk, spot (1,14). Staff baharu muncul di sini |
| 1 | `reception`, `frontdesk` | Reception Counter / Front Desk | Kekal seperti sekarang (hideLabel) |
| 1 | `auditorium`* | Launch Auditorium | c1..8 r1..9. DECOR `stage` r=2 (c2..8, disekat), `stage_screen` r=1; `podium` + `speaker_stack` di apron r=3; 4 baris x 7 seats (r5..8, lorong c=5) menghadap pentas (28); 3 stand penceramah di r=3 dan 4 stand belakang r=9; rug carpet; WALL_DECOR `wall_banner_a` |
| 1 | `meeting` | Meeting Room | c10..12 r3..6 (meja + 3 seats + stands) |
| 1 | `training`* | Training Room | Bilik kaca c15..20 r1..8 (`glass_b` c=14/21, `glass_a` r=9, pintu di c=17), whiteboard + projector_screen, 10 meja latihan + seats (lorong tengah c=17), 2 stand trainer, rug carpet |
| 1 | `client`* | Client Space | c6..19 r10..12: tiga set sofa + coffee_table, seats r12, cooler |
| 1 | `playroom` | Chill Area | r14..19: snooker c6..8, ping-pong c11..12, foosball c15..16, dart (papan dinding B, stand c=3), lounge sofa + coffee_table (r18..19). Rug checker dikongsi dengan Gaming |
| 1 | `gaming` | Gaming Area | Arcade x4 (c13..16 r18), TV console (c18..19 r15) + 4 beanbag (stands act `play`) |
| 1 | `pantry` | Pantry | Mesin berjenama, `capacity: 2`, queue, kekal di sayap kanan atas |
| 1 | `toilet` | Toilet | Sayap kanan bawah |
| 2 | `marketing`* | Marketing Department | Meja `desk` |
| 2 | `kanban` | Marketing Plan | Papan tugas (stand), dalam kawasan marketing |
| 2 | `sales` | Sales Department | 12 meja `desk` (seats auto): r10 dan r13, c11..13 dan c16..18 (tempat bekas big meeting room) |
| 2 | `head_office`* | Head of Department | Bilik kaca, `exec_desk` + seat, 2 stand pelawat |
| 2 | `approval` | Approval | Loceng di pintu bilik Head of Department |
| 2 | `frontend`, `backend`, `qa`, `research`, `deploy`, `ops` | IT · Frontend / IT · Backend / IT · QA / IT · Research / IT · DevOps / IT · Ops | Kluster meja IT Department |
| 2 | `coffee` | Big Pantry · Coffee | Mesin kopi, kaunter pantri, peti sejuk |
| 2 | `water_cooler` | Big Pantry · Lounge | SATU meja di sebelah sofa + cooler (tiada meja kerja/makan lain) |
| 2 | `toilet_2`* | Toilet L2 | |
| 2 | `outdoor_chill`* | Outdoor Chill | Teres luar: dek, kerusi rehat, payung |
| 3 | `ceo`*, `cfo`*, `md`*, `hod`* | CEO Office / CFO Office / MD Office / HOD Office | Bilik kaca, `exec_desk` + 1 seat + 2 stand pelawat |
| 3 | `boardroom` | Big Meeting Room | c8..18 r9..15 di tengah L3: `boardtable` 9x2 (r11..12), 9 seats (r13) + 26 stands = 35 (>= 30), projector + whiteboard di r=9, rug carpet. Dekor lounge eksekutif (sofa, coffee_table, pokok) tanpa department |
| 4 | `rooftop`* | Garden & Party | Taman kiri (grass c2..8), BBQ + bar + DJ atas, umbrella kanan bawah. >= 16 stands (29), sebahagian act `drink` dekat BBQ/bar |
| 4 | `pool`* | Swimming Pool | Dek kolam renang: stands di tebing (24, sebahagian act `drink`), kerusi rehat dan umbrella_table |

Dibuang: `outdoor_work` dan `outdoor_desk` (L3). `sales` pindah L1 -> L2, `boardroom` L2 -> L3, `playroom` dan `gaming` L3 -> L1.
Sweep chill masih hantar ke `playroom` (kini L1). Approval di L2 (pintu Head of Department).

### Rooftop

- Kolam: `ZONES` tile `water` (sprite `water_a` / `water_b`, dilukis atas dek) pada c10..18 r9..12. Setiap sel air
  disekat melalui DECOR `{ floor: 4, kind: 'block', cells }` (kind `block` = penyekat tak nampak, enjin tak lukis).
  `pool_ladder` (19,11) dan `diving_board` (14,8) di tebing.
- Taman: grass c2..8 r5..18, `garden_tree`, `flower_bed`, `fountain` (5,11, tanpa FX), `planter`, `plant`.
- Party: `dj_booth` (22,4) + `speaker_stack`, `bar_counter` (c16..18 r3), `bbq` (c12..13 r3), `balloons`, `party_table`,
  `umbrella_table`, `lounger`.
- Pagar kaca di semua tepi, `ac_unit`, `stair_hut` (26,10) dan landing (25,10) kekal.

## Bentuk data `resources/js/office/layout.js`

```js
export const GRID, TILE, ORIGIN, CANVAS               // sama macam dulu (ORIGIN = unjuran setempat setiap aras)
export const FLOORS = [{ id, key, label, name, walls }]  // 4 entri
export const STAIRS = { cell, landing }
export const DEPARTMENTS = { key: { floor, label, spot, cells, seats?, stands?, queue?, capacity?, hideLabel? } }
export const DECOR = [{ floor, kind, cells }]          // disekat (kind 'plant' pun disekat; kind 'block' = penyekat tak nampak, tidak dilukis)
export const ZONES = [{ floor, c0, r0, c1, r1, color?, alpha?, tile? }]
//   tile: 'deck' | 'grass' | 'carpet' | 'water'  -> enjin guna sprite `${tile}_a` / `${tile}_b` (checker) gantikan lantai kayu
//   color/alpha: tint permaidani seperti sekarang
export const WALL_DECOR = [{ floor, key, wall: 'A' | 'B', u, vTop }]   // sprite dinding (window, poster, door...)
export const FLOOR_FX = [{ floor, kind: 'steam' | 'bubbles' | 'pong', c, r }]  // kesan ambien
export const DEPT_BUBBLE, VENDOR_COLORS, AVATARS, AVATAR_LABELS, VISITOR_STYLES, STYLE_SHIRT

export function floorOf(dept)          // aras department (lalai 1)
export function blockedTiles(floor)    // Set 'c,r' untuk aras itu (termasuk STAIRS.cell)
export function seatsFor(dept), standsFor(dept), capacityFor(dept), queueFor(dept), spotFor(dept)
export function allSeats(floor)        // [{ c, r, dept }] untuk aras itu
export function departmentsOn(floor)   // [key, ...]
```

Furniture `cells[].kind` dan `DECOR.kind` = nama fail PNG di `public/assets/office/` (anchor bawah-tengah pada
tengah tile + 14px, lebar 56). Sofa/kerusi/beanbag berwarna ikut nama, cth. `sofa_blue`, `beanbag_red`.

## Sprite baharu (`tools/make_sprites.py`)

Furniture (tile, disekat): `stage`, `stage_screen`, `podium`, `speaker_stack` (auditorium L1); `pool_ladder`, `diving_board`,
`garden_tree`, `flower_bed`, `fountain`, `dj_booth`, `bar_counter`, `balloons`, `party_table` (rooftop); sprite dinding
`wall_banner_a`. Sedia ada: `stairs`, `stair_hut`, `training_desk`, `projector_screen`, `whiteboard`, `coffee_table`,
`exec_desk`, `glass_a`, `glass_b` (dinding pejabat kaca, geometri sama `partition_a` / `partition_b`), `arcade`,
`tv_console`, `beanbag_blue`, `beanbag_red`, `beanbag_yellow`, `beanbag_green`, `umbrella_table`, `lounger`, `bbq`,
`planter`, `ac_unit`, `pantry_counter`, `railing_a`, `railing_b` (pagar kaca tepi; `_a` sepanjang
paksi c iaitu tepi hadapan r=19, `_b` sepanjang paksi r iaitu tepi hadapan c=27; untuk tepi belakang rooftop guna
sprite sama).

Jubin lantai (56 x 28, tidak disekat): `deck_a`, `deck_b`, `grass_a`, `grass_b`, `carpet_a`, `carpet_b`, `water_a`, `water_b` (air kolam, dilukis atas dek).

Gaya staff baharu: `exec` (lelaki, sut + tali leher) dan `exec_w` (wanita, blazer + skirt pensel). Tint shirt:
`exec` 0x1f2a44, `exec_w` 0x3b2a4a. Tambah ke `AVATARS` (JS dan PHP), label 'Eksekutif' / 'Eksekutif (wanita)'.

## Enjin dan UI

- Setiap aras dilukis pada ofset dunia sendiri (bangunan bertingkat, L1 paling bawah). Objek aras tinggi
  di depan aras rendah (jalur depth berasingan setiap aras).
- Paparan "Bangunan" (overview): kamera muat semua aras. Klik satu aras: zoom penuh ke aras itu. Butang
  "Kembali ke bangunan". Tab HTML di atas canvas: Bangunan, L1, L2, L3, Rooftop dengan kiraan staff.
- Staff tukar aras ikut tangga: jalan ke `landing`, animasi naik/turun ke `landing` aras sebelah (satu aras
  setiap langkah), sambung jalan. Tempat duduk dikunci ikut `floor:c,r`.
- Snapshot pertama: staff terus diletak di aras dan tempat mereka (tak jalan dari pintu). Agent baharu kemudian
  muncul di pintu L1.
- Klik staff di senarai Team: zoom ke aras staff itu. Mod TV: pusing Bangunan -> L1 -> L2 -> L3 -> Rooftop.
- Pilihan department di borang butiran dikumpul ikut aras (optgroup).
