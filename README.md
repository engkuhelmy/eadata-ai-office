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

`php artisan office:demo` (atau `scripts\start-demo.ps1`) jalankan 13 staff demo (briefing boardroom, kerja, tandas, pantri maks 2 orang, chill room) dan **modul reception**:

- Penyambut tetamu AI **Reni** (`demo-reception`, avatar `recep`) duduk di kaunter reception (department `frontdesk`). Jumlah staff demo = 14.
- Penghantar Grab, ShopeeFood, J&T dan DHL (`demo-visit-<brand>-<n>`) tiba bergilir satu demi satu: muncul di pintu (`door`), loceng berbunyi, masuk ke kaunter sahaja (`reception`), serah makanan/parcel, kemudian keluar (`session_end`). Barisnya dipadam ~25s selepas keluar.
- Lepas tiap serahan Reni buat pusingan 3-4 hentian (mula di meja penerima) hantar arahan, kemudian pulang ke `frontdesk`. Tiada penghantaran 3 minit = Reni buat pusingan sendiri.
- Matikan modul: `php artisan office:demo --no-reception`.
- Sesi staff `demo-*` tak pernah ditamatkan; hanya penghantar (`demo-visit-*`) tamat sendiri. Logik di `app/Office/Demo/ReceptionModule.php`.

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
