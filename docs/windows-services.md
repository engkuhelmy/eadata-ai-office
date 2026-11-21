# AI Office Hub di Windows: autostart, log dan health

Ada 4 proses PHP yang perlu hidup:

| Nama | Command | Port |
|---|---|---|
| serve | `php artisan serve --host=127.0.0.1 --port=8000 --no-reload` (env `PHP_CLI_SERVER_WORKERS=4`) | 8000 |
| reverb | `php artisan reverb:start` | 8081 (`REVERB_SERVER_PORT`; 8080 dah dipakai svchost) |
| queue | `php artisan queue:work --tries=3 --sleep=1` | - |
| schedule | `php artisan schedule:work` | - |

> `--no-reload` perlu supaya Laravel hormati `PHP_CLI_SERVER_WORKERS`. Di Windows, PHP built-in
> server mungkin tetap single-worker (multi-worker ialah ciri Unix); tak bahaya, cuma tak laju lebih.

PHP tiada dalam PATH di PC ini. Semua script cari `php` dalam PATH dulu, kalau tiada guna
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\PHP.PHP.8.3_*\php.exe`.

## Pilihan A: skrip + Task Scheduler (disyorkan)

### Start / stop manual

```powershell
cd "C:\Users\Helmi\Desktop\ai office virtual 3D"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1 -Dry   # tengok dulu
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-office.ps1
```

`start-office.ps1` skip service yang dah running (detect ikut command line), start dengan
tetingkap tersembunyi, dan print jadual health. `stop-office.ps1` hanya bunuh proses php
yang berkaitan projek ini (path projek atau command artisan di atas). Kedua-duanya boleh
dipanggil dari cwd mana-mana.

### Autostart bila log on

Script ini **mengubah sistem** jadi **user kena run sendiri**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1 -Dry   # tengok rancangan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1         # daftar
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1 -Force  # ganti task sedia ada
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\unregister-autostart.ps1       # buang
```

Task bernama **AI Office Hub**, trigger *At log on*, run level *Limited* (bukan admin),
dijalankan sebagai user semasa. Uji tanpa reboot: `Start-ScheduledTask -TaskName 'AI Office Hub'`
kemudian semak health (bawah). Sahkan service masih hidup selepas task selesai; kalau mati
sebaik task tamat, guna Pilihan B (NSSM).

Kelemahan: hanya start bila user log on, dan tak auto-restart bila satu proses crash
(jalankan `start-office.ps1` semula, ia hanya start yang mati). NSSM lebih tahan.

## Pilihan B: NSSM (service sebenar, auto-restart)

Perlu PowerShell **as Administrator**. NSSM = Non-Sucking Service Manager.

```powershell
winget install NSSM.NSSM
```

Ganti `$php` dan `$root` ikut PC anda:

```powershell
$root = 'C:\Users\Helmi\Desktop\ai office virtual 3D'
$php  = (Get-Command php -ErrorAction SilentlyContinue).Source
if (-not $php) { $php = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\PHP.PHP.8.3_*\php.exe" | Select -First 1).FullName }
```

Service jalan sebagai LocalSystem secara default; `%LOCALAPPDATA%` lain untuk akaun itu, jadi
pastikan `$php` ialah path penuh (seperti di atas) dan, kalau perlu akses fail user, set
`nssm set <svc> ObjectName .\Helmi <password>` (**anda sendiri** masukkan kata laluan).

```powershell
# 1) Web
nssm install OfficeServe $php "artisan serve --host=127.0.0.1 --port=8000 --no-reload"
nssm set OfficeServe AppDirectory $root
nssm set OfficeServe AppEnvironmentExtra PHP_CLI_SERVER_WORKERS=4
nssm set OfficeServe AppStdout "$root\storage\logs\ops-serve.out.log"
nssm set OfficeServe AppStderr "$root\storage\logs\ops-serve.err.log"

# 2) Reverb
nssm install OfficeReverb $php "artisan reverb:start"
nssm set OfficeReverb AppDirectory $root
nssm set OfficeReverb AppStdout "$root\storage\logs\ops-reverb.out.log"
nssm set OfficeReverb AppStderr "$root\storage\logs\ops-reverb.err.log"

# 3) Queue
nssm install OfficeQueue $php "artisan queue:work --tries=3 --sleep=1"
nssm set OfficeQueue AppDirectory $root
nssm set OfficeQueue AppStdout "$root\storage\logs\ops-queue.out.log"
nssm set OfficeQueue AppStderr "$root\storage\logs\ops-queue.err.log"

# 4) Scheduler
nssm install OfficeSchedule $php "artisan schedule:work"
nssm set OfficeSchedule AppDirectory $root
nssm set OfficeSchedule AppStdout "$root\storage\logs\ops-schedule.out.log"
nssm set OfficeSchedule AppStderr "$root\storage\logs\ops-schedule.err.log"

# Pilihan biasa untuk semua: auto-start, restart bila crash, rotate log
foreach ($s in 'OfficeServe','OfficeReverb','OfficeQueue','OfficeSchedule') {
  nssm set $s Start SERVICE_AUTO_START
  nssm set $s AppExit Default Restart
  nssm set $s AppRestartDelay 3000
  nssm set $s AppRotateFiles 1
  nssm set $s AppRotateBytes 5242880
}
nssm set OfficeQueue DependOnService OfficeServe   # pilihan: tertib start

Start-Service OfficeServe, OfficeReverb, OfficeQueue, OfficeSchedule
```

Buang:

```powershell
foreach ($s in 'OfficeServe','OfficeReverb','OfficeQueue','OfficeSchedule') { nssm stop $s; nssm remove $s confirm }
```

Jangan guna Pilihan A dan B serentak (port bertembung). Kalau pindah ke NSSM, jalankan
`unregister-autostart.ps1` dan `stop-office.ps1` dulu.

Selepas ubah `.env` atau deploy kod: `Restart-Service OfficeServe, OfficeReverb, OfficeQueue, OfficeSchedule`
(queue:work menyimpan kod lama dalam memori; wajib restart/`php artisan queue:restart`).

## Lokasi log

| Fail | Isi |
|---|---|
| `storage\logs\ops-serve.out.log` / `.err.log` | access log & error `artisan serve` |
| `storage\logs\ops-reverb.out.log` / `.err.log` | Reverb websocket |
| `storage\logs\ops-queue.out.log` / `.err.log` | queue worker |
| `storage\logs\ops-schedule.out.log` / `.err.log` | scheduler |
| `*.log.1` | generasi sebelum (start-office.ps1 simpan satu salinan) |
| `storage\logs\laravel.log` | log aplikasi Laravel |
| Scheduled Task | Task Scheduler -> AI Office Hub -> History (kena enable) |

Tengok live: `Get-Content storage\logs\ops-serve.err.log -Wait -Tail 50`

## Semak health

Cara mudah: jalankan `scripts\start-office.ps1`, ia print jadual (HTTP `/up`, `/login`, TCP 8000, 8081)
dan tak start semula yang dah running.

Manual:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/up -UseBasicParsing | Select StatusCode
Invoke-WebRequest http://127.0.0.1:8000/login -UseBasicParsing | Select StatusCode
Test-NetConnection 127.0.0.1 -Port 8000
Test-NetConnection 127.0.0.1 -Port 8081
Get-CimInstance Win32_Process -Filter "Name='php.exe'" | Select ProcessId, CommandLine | Format-List
Get-ScheduledTask -TaskName 'AI Office Hub' | Get-ScheduledTaskInfo
```

Kalau tunnel digunakan: `Get-Service cloudflared` dan `cloudflared tunnel info office-hub`.

## Pasang semula hook (kalau config agent ditulis ganti)

Claude Code, Codex atau Hermes kadang-kadang timpa fail config/hook (update tool, reset setting).
Gejala: event berhenti masuk ke office. Pasang semula; token dari `php artisan office:device`:

```powershell
cd "C:\Users\Helmi\Desktop\ai office virtual 3D"
python hooks\install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes --dry-run
python hooks\install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes
```

- Buang `--dry-run` untuk pasang betul-betul. `--uninstall` untuk buang.
- Hook sentiasa tunjuk ke `http://127.0.0.1:8000` walaupun guna Cloudflare Tunnel.
- Codex: lepas pasang, jalankan `/hooks` dalam Codex untuk trust.
- Hook spool event bila server offline dan hantar semula bila online, jadi restart pendek tak hilang data.
