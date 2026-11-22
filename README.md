# eadata-ai-office

Virtual office isometric pixel art dalam browser yang tunjuk semua AI agent dalam PC sebagai "staff". Setiap sesi agent (Claude Code, Codex, Hermes, atau skrip generic) jalan ke meja department ikut jenis kerja, dengan bubble task di atas kepala.

Stack: Laravel 12 (PHP 8.3), Reverb (WebSocket) dengan fallback polling, Phaser 3 (Vite), SQLite.

## Jalankan (lokal)

```powershell
composer install
npm install
copy .env.example .env
php artisan key:generate
php artisan migrate
npm run build
```

Tambah nilai `REVERB_APP_ID`, `REVERB_APP_KEY`, `REVERB_APP_SECRET` dan `VITE_REVERB_*` dalam `.env` (rujuk `.env.example`).

Jalankan setiap satu dalam terminal sendiri:

```powershell
php artisan serve
php artisan reverb:start
php artisan queue:work
```

Cipta user dan device token:

```powershell
php artisan office:user kau@local.test --role=owner
php artisan office:device nama-pc
```

Simulasi team 5 agent: `php artisan office:simulate --ticks=40 --delay=2`

## Hook agent sebenar

`hooks/office-hook.py` tangkap event, redact (isi fail tak pernah dihantar), dan hantar ke `/api/ingest`. Offline akan di-spool dan dihantar semula.

```powershell
python hooks\install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes --dry-run
```

Buang `--dry-run` untuk pasang. `--uninstall` untuk buang. Codex perlu `/hooks` trust selepas pasang.

## Demo 24 jam

`php artisan office:demo` (atau `scripts\start-demo.ps1`) jalankan demo dalam bangunan 4 aras (L1, L2, L3, Rooftop; kontrak di `docs/multifloor-spec.md`). Jumlah staff demo = **26**: 13 staff IT + 12 staff aras + penyambut tetamu Reni.

- **Lantai**: L1 = pintu, reception, bilik kaca `training`, `meeting` (client meeting), `auditorium` (pentas pelancaran), `client`, zon Chill & Game (`playroom` + `gaming`), pantri, tandas. L2 = `sales`, marketing, head office, kanban, approval, IT, big pantry (`coffee`), `toilet_2`, `outdoor_chill`. L3 = `ceo`, `cfo`, `md`, `hod` dan `boardroom` (Big Meeting Room). Rooftop = taman / dek parti (`rooftop`) + kolam renang (`pool`). Kunci `outdoor_work` sudah dibuang (PATCH department itu ditolak 422).
- **Staff IT (L2, 13 orang)**: 5 staff team (kanban, kerja di meja, minum di pantri) dan 8 rotator (kerja -> tandas L2 `toilet_2` -> pantri -> chill rawak di `playroom` / `gaming` / `pool` / `rooftop` / `outdoor_chill`).
- **Briefing**: awal setiap kitaran team + rotator + staff aras (25 orang) berkumpul di `boardroom` (Big Meeting Room, L3). Reni kekal di kaunter.
- **Modul staff aras** (`app/Office/Demo/FloorStaffModule.php`, 12 orang): setiap seorang pusing ikut rutin peribadi (bubble = teks tugas, cth. "Semak bajet Q4"; ping `idle` tiap ~20s supaya sweep tak pindahkan mereka).
  - L3: CEO **Datuk Hafiz**, CFO **Mei Ling**, MD **Rajesh**, HOD **Puan Rosnah** (avatar `exec` / `exec_w`): pejabat sendiri + lawatan (head_office, boardroom, sales, big pantry, IT, `pool`, `rooftop`, gaming, marketing, training, outdoor_chill).
  - L2: Head of Department **Encik Kamal** (head_office, marketing, qa, kanban); Marketing **Farah** dan **Iqbal** (marketing, kanban, mesyuarat klien L1, big pantry, outdoor_chill); Sales **Amir** dan **Liyana** (sales di L2; lawat `client`, `meeting`, `auditorium`, pantri L1).
  - L1: trainer **Cikgu Azlan** (bilik kaca `training` + `auditorium`); intern **Danial** dan **Sara** (training, toilet, client, auditorium).
- **Acara demo** (dalam `FloorStaffModule`, dipacu tick, ikut `--speed`):
  - **Pelancaran produk**: ~3 min lepas mula, kemudian setiap ~6-8 min, ~90s di `auditorium`. Cikgu Azlan membentang ("Pelancaran produk baharu"); penonton Farah, Iqbal, Amir, Liyana, Danial, Sara dan Puan Rosnah ("Hadir pelancaran produk"), lepas tu mereka sambung rutin.
  - **Pool party**: ~5 min lepas mula, kemudian setiap ~10-12 min, ~75s di `pool` / `rooftop` ("Pool party!" / "Bakar BBQ di rooftop"): 6-8 staff aras + rotator rawak (bukan yang di pantri), lepas tu kembali ke rutin / peringkat rotator.
  - Acara tak jalan semasa briefing semua staff (briefing batalkan acara yang sedang jalan).
- **Pantri L1** maks 2 orang serentak: team, rotator, staff aras dan Reni kongsi pintu yang sama (penuh = tunggu / langkau).
- **Modul reception** (`app/Office/Demo/ReceptionModule.php`): Reni (`demo-reception`, avatar `recep`) di kaunter (`frontdesk`). Penghantar Grab, ShopeeFood, J&T dan DHL (`demo-visit-<brand>-<n>`) tiba satu demi satu di L1: pintu (`door`), loceng, kaunter sahaja (`reception`), serah barang, keluar (`session_end`); barisnya dipadam ~25s kemudian. Lepas tiap serahan Reni buat pusingan 3-4 hentian (mula di meja penerima) merentasi seluruh bangunan, kemudian pulang ke `frontdesk`. Tiada penghantaran 3 minit = Reni buat pusingan sendiri.
- Pilihan: `--hours=24`, `--speed=1`, `--once`, `--no-reception` (tanpa Reni + penghantar), `--no-floors` (tanpa 12 staff aras dan acara mereka), `--no-events` (staff aras jalan, tanpa pelancaran produk + pool party).
- Sesi staff `demo-*` tak pernah ditamatkan; hanya penghantar (`demo-visit-*`) tamat sendiri.
- Kunci department baharu (`training`, `sales`, `client`, `marketing`, `head_office`, `toilet_2`, `outdoor_chill`, `ceo`, `cfo`, `md`, `hod`, `gaming`, `auditorium`, `pool`, `rooftop`) boleh di-pin oleh owner. Routing automatik hook masih guna kunci lama.

## Ujian

```powershell
php artisan test
python -m unittest discover -s hooks/tests
```

## Aset sprite

Sprite dijana oleh `python tools\make_sprites.py` (perlu Pillow) ke `public/assets/office/`.

Rujukan penuh: [AI-OFFICE-HUB-BUILD.md](AI-OFFICE-HUB-BUILD.md).

## Operasi

Skrip untuk run harian di Windows (semua boleh dipanggil dari cwd mana-mana; guna `-Dry` untuk tengok dulu):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1      # start serve, reverb, queue, schedule + jadual health
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-office.ps1       # stop proses projek ini sahaja
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1   # Scheduled Task "AI Office Hub" (USER run sendiri)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\unregister-autostart.ps1  # buang task tu
```

Log di `storage\logs\ops-*.log`. Panduan lanjut:

- [docs/windows-services.md](docs/windows-services.md): autostart (Task Scheduler atau NSSM), log, health check, pasang semula hook.
- [docs/cloudflare-tunnel.md](docs/cloudflare-tunnel.md): expose `office.eadata.my` guna Cloudflare Tunnel + Access (email OTP), nilai `.env`, troubleshooting.

Set `TRUSTED_PROXIES=*` dalam `.env` bila di belakang tunnel/proxy (lihat `bootstrap/app.php`).
