# Bangunan 4 aras: kontrak antara modul

Spec ini dikongsi oleh empat bahagian kerja: sprite, backend/demo, pelan lantai (`layout.js`) dan enjin/UI.
Ikut nama dan bentuk data di sini dengan tepat.

## Aras

| id | Tab | Isi |
|----|-----|-----|
| 1 | L1 | Pintu masuk + reception, training area, meeting room (client), sales department, client space, toilet, pantry berjenama (maks 2 orang), tangga |
| 2 | L2 | Marketing department, Head of Department office, big meeting room (boardroom), IT department, big pantry, toilet, outdoor chill (teres), tangga |
| 3 | L3 | Pejabat CEO, CFO, MD, HOD (Heads of Department), chill area (snooker/dart/pong/foos), gaming area, outdoor working area, tangga |
| 4 | Rooftop | Taman rooftop: dek, rumput, BBQ, payung, kerusi rehat, pokok, unit aircond, pondok tangga. Tiada dinding, pagar kaca di semua tepi |

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
| 1 | `training`* | Training Area | Meja latihan berderet (seats) + whiteboard/projector, 1-2 stand trainer di depan |
| 1 | `meeting` | Meeting Room | Bilik mesyuarat klien (meja + seats + stands) |
| 1 | `sales`* | Sales Department | Meja `desk` (seats auto) |
| 1 | `client`* | Client Space | Sofa + coffee_table, seats/stands untuk pelanggan |
| 1 | `pantry` | Pantry | Mesin berjenama, `capacity: 2`, queue, kekal di sayap kanan atas |
| 1 | `toilet` | Toilet | Sayap kanan bawah |
| 2 | `marketing`* | Marketing Department | Meja `desk` |
| 2 | `kanban` | Marketing Plan | Papan tugas (stand), dalam kawasan marketing |
| 2 | `head_office`* | Head of Department | Bilik kaca, `exec_desk` + seat, 2 stand pelawat |
| 2 | `approval` | Approval | Loceng di pintu bilik Head of Department |
| 2 | `boardroom` | Big Meeting Room | Meja panjang. Mesti muat 24 orang: seats + stands ≥ 24 (briefing semua staff demo) |
| 2 | `frontend`, `backend`, `qa`, `research`, `deploy`, `ops` | IT · Frontend / IT · Backend / IT · QA / IT · Research / IT · DevOps / IT · Ops | Kluster meja IT Department |
| 2 | `coffee` | Big Pantry · Coffee | Mesin kopi, kaunter pantri, peti sejuk |
| 2 | `water_cooler` | Big Pantry · Lounge | Meja makan/sofa dalam big pantry |
| 2 | `toilet_2`* | Toilet L2 | |
| 2 | `outdoor_chill`* | Outdoor Chill | Teres luar: dek, kerusi rehat, payung |
| 3 | `ceo`*, `cfo`*, `md`*, `hod`* | CEO Office / CFO Office / MD Office / HOD Office | Bilik kaca, `exec_desk` + 1 seat + 2 stand pelawat |
| 3 | `playroom` | Chill Area | Snooker, dart, pong, foos (stands act play/dart) |
| 3 | `gaming`* | Gaming Area | Arcade, TV console + beanbag (stands act `play`) |
| 3 | `outdoor_work`* | Outdoor Working | Dek luar, `outdoor_desk` + seats, payung |
| 4 | `rooftop`* | Rooftop | Banyak stands (≥ 16), sebahagian act `drink` dekat BBQ |

Sweep chill masih hantar ke `playroom` (kini L3). Approval kini di L2 (pintu Head of Department).

## Bentuk data `resources/js/office/layout.js`

```js
export const GRID, TILE, ORIGIN, CANVAS               // sama macam dulu (ORIGIN = unjuran setempat setiap aras)
export const FLOORS = [{ id, key, label, name, walls }]  // 4 entri
export const STAIRS = { cell, landing }
export const DEPARTMENTS = { key: { floor, label, spot, cells, seats?, stands?, queue?, capacity?, hideLabel? } }
export const DECOR = [{ floor, kind, cells }]          // disekat (kecuali kind 'plant' tetap disekat juga)
export const ZONES = [{ floor, c0, r0, c1, r1, color?, alpha?, tile? }]
//   tile: 'deck' | 'grass' | 'carpet'  -> enjin guna sprite `${tile}_a` / `${tile}_b` (checker) gantikan lantai kayu
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

Furniture (tile, disekat): `stairs`, `stair_hut`, `training_desk`, `projector_screen`, `whiteboard`, `coffee_table`,
`exec_desk`, `glass_a`, `glass_b` (dinding pejabat kaca, geometri sama `partition_a` / `partition_b`), `arcade`,
`tv_console`, `beanbag_blue`, `beanbag_red`, `beanbag_yellow`, `beanbag_green`, `umbrella_table`, `lounger`, `bbq`,
`planter`, `outdoor_desk`, `ac_unit`, `pantry_counter`, `railing_a`, `railing_b` (pagar kaca tepi; `_a` sepanjang
paksi c iaitu tepi hadapan r=19, `_b` sepanjang paksi r iaitu tepi hadapan c=27; untuk tepi belakang rooftop guna
sprite sama).

Jubin lantai (56 x 28, tidak disekat): `deck_a`, `deck_b`, `grass_a`, `grass_b`, `carpet_a`, `carpet_b`.

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
