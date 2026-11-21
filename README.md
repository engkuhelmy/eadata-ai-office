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

## Ujian

```powershell
php artisan test
python -m unittest discover -s hooks/tests
```

## Aset sprite

Sprite dijana oleh `python tools\make_sprites.py` (perlu Pillow) ke `public/assets/office/`.

Rujukan penuh: [AI-OFFICE-HUB-BUILD.md](AI-OFFICE-HUB-BUILD.md).
