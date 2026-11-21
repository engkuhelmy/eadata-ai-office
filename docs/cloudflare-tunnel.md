# Expose AI Office Hub guna Cloudflare Tunnel + Access

Panduan untuk buka `https://office.eadata.my` dari internet tanpa buka port router, dengan
Cloudflare Access (email OTP) di depan, dan login Laravel di belakang. Semua service
kekal di PC Windows ini (`127.0.0.1`).

```
Browser --https/wss--> Cloudflare (Access OTP) --tunnel--> cloudflared (PC ini)
                                                              |-- /app/*, /apps/* --> localhost:8081 (Reverb)
                                                              |-- selebihnya       --> localhost:8000 (artisan serve)
Hook agent (Claude/Codex/Hermes) --http--> 127.0.0.1:8000/api/ingest   (TAK lalu tunnel)
```

## Siapa buat apa

Langkah bertanda **[USER SAHAJA]** perlu akaun Cloudflare / akses dashboard / login interaktif.
Tool atau agent tak boleh buat bagi pihak anda.

| Langkah | Siapa |
|---|---|
| Letak nameserver `eadata.my` ke Cloudflare (di registrar) | **[USER SAHAJA]** |
| `cloudflared tunnel login` (buka browser, authorize zon) | **[USER SAHAJA]** |
| Cipta Access application + policy (email dibenarkan) | **[USER SAHAJA]** |
| `cloudflared service install` (perlu PowerShell Administrator) | **[USER SAHAJA]** |
| Edit `.env`, `npm run build`, restart service | boleh dibantu |

## 0. Prasyarat

1. Domain `eadata.my` DNS-nya diurus Cloudflare (zon status **Active**). Kalau belum:
   tambah site di dashboard Cloudflare, lepas tu tukar nameserver di registrar ikut yang
   Cloudflare bagi. **[USER SAHAJA]**
2. Akaun Cloudflare Zero Trust (plan Free cukup untuk <= 50 user). Pilih "team name" bila
   diminta kali pertama.
3. AI Office Hub dah jalan lokal (`scripts\start-office.ps1`, health OK di `http://127.0.0.1:8000`).

## 1. Install cloudflared

```powershell
winget install Cloudflare.cloudflared
```

Tutup dan buka semula PowerShell supaya `cloudflared` ada dalam PATH, lepas tu `cloudflared --version`.

## 2. Login, cipta tunnel, route DNS

```powershell
cloudflared tunnel login                         # [USER SAHAJA] browser terbuka -> pilih eadata.my -> Authorize
cloudflared tunnel create office-hub             # catat UUID + lokasi <UUID>.json
cloudflared tunnel route dns office-hub office.eadata.my
```

`tunnel login` simpan `cert.pem` di `C:\Users\<nama>\.cloudflared\`. `tunnel create` hasilkan
fail credentials `C:\Users\<nama>\.cloudflared\<UUID>.json` (rahsia, jangan commit / kongsi).
`route dns` cipta CNAME `office` -> `<UUID>.cfargotunnel.com` (proxied) secara automatik.

## 3. config.yml

Cipta `C:\Users\<nama>\.cloudflared\config.yml` (ganti `<UUID>` dan `<nama>`):

```yaml
tunnel: <UUID>
credentials-file: C:\Users\<nama>\.cloudflared\<UUID>.json

ingress:
  # 1) WebSocket + API dalaman Reverb -> port 8081 (MESTI di atas)
  - hostname: office.eadata.my
    path: ^/(app|apps)/
    service: http://localhost:8081
  # 2) Selebihnya (web, /login, /api/*, aset Vite) -> artisan serve
  - hostname: office.eadata.my
    service: http://localhost:8000
  # 3) Catch-all wajib
  - service: http_status:404
```

Susunan penting: cloudflared padan rule dari atas ke bawah, jadi rule path `^/(app|apps)/`
mesti sebelum rule 8000. `path` ialah regex pada URL path.

Semak sintaks (tak start apa-apa):

```powershell
cloudflared tunnel ingress validate
cloudflared tunnel ingress rule https://office.eadata.my/app/test   # patut padan rule 8081
cloudflared tunnel ingress rule https://office.eadata.my/login      # patut padan rule 8000
```

## 4. Jalankan sebagai Windows service

Buka PowerShell **as Administrator** **[USER SAHAJA]**:

```powershell
cloudflared service install
Start-Service cloudflared
Get-Service cloudflared
```

Gotcha Windows: service jalan sebagai `LocalSystem`, jadi ia mungkin cari config di
`C:\Windows\System32\config\systemprofile\.cloudflared\` dan bukannya folder user anda.
Kalau service start tapi tunnel tak connect / "no ingress rules", salin fail:

```powershell
$dst = 'C:\Windows\System32\config\systemprofile\.cloudflared'
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item "$env:USERPROFILE\.cloudflared\config.yml", "$env:USERPROFILE\.cloudflared\<UUID>.json" $dst
# edit $dst\config.yml: credentials-file -> C:\Windows\System32\config\systemprofile\.cloudflared\<UUID>.json
Restart-Service cloudflared
```

Uji manual dulu (foreground, Ctrl+C untuk henti): `cloudflared tunnel run office-hub`.

## 5. Cloudflare Access (email OTP) **[USER SAHAJA]**

Di dashboard **Zero Trust** (one.dash.cloudflare.com):

1. **Settings -> Authentication -> Login methods**: pastikan **One-time PIN** aktif (default aktif).
2. **Access -> Applications -> Add an application -> Self-hosted**.
   - Application name: `AI Office Hub`
   - Session duration: contoh `24 hours`
   - Public hostname: subdomain `office`, domain `eadata.my`, path kosong (lindungi seluruh hos,
     termasuk `/app/*` untuk websocket).
3. **Policies -> Add policy**:
   - Name: `Owner email`, Action: **Allow**
   - Include: **Emails** -> senarai emel anda sahaja (atau **Emails ending in** `@eadata.my`).
4. Identity providers: pilih One-time PIN. Save.
5. Uji dalam tetingkap incognito: buka `https://office.eadata.my` -> halaman Access minta emel ->
   PIN dihantar ke emel -> masuk -> baru nampak login Laravel.

Selepas ini ada **dua** lapisan: Access (emel OTP) kemudian login Laravel (akaun office).

## 6. Nilai `.env` (di server)

Ubah `.env` projek (jangan commit):

```dotenv
APP_ENV=production
APP_DEBUG=false
APP_URL=https://office.eadata.my
SESSION_SECURE_COOKIE=true
TRUSTED_PROXIES=*

# --- Sisi server (Laravel -> Reverb, semua dalam PC ini, tak lalu Cloudflare) ---
REVERB_HOST=127.0.0.1
REVERB_PORT=8081
REVERB_SCHEME=http
REVERB_SERVER_PORT=8081

# --- Sisi browser (Echo, dibake masa build Vite) --- tulis literal, JANGAN guna ${REVERB_HOST}
VITE_REVERB_HOST=office.eadata.my
VITE_REVERB_PORT=443
VITE_REVERB_SCHEME=https
```

`REVERB_APP_ID`, `REVERB_APP_KEY`, `REVERB_APP_SECRET` kekal seperti sedia ada dan
`VITE_REVERB_APP_KEY="${REVERB_APP_KEY}"` kekal.

Kenapa dua set? Server Laravel broadcast ke Reverb terus di `127.0.0.1:8081` (HTTP, laju, tak
perlu Access). Browser pula sambung `wss://office.eadata.my:443/app/<key>` melalui tunnel,
dan rule `^/(app|apps)/` hantar ke 8081.

Pembolehubah `VITE_*` **dibake ke dalam JS masa build**, jadi wajib build semula:

```powershell
npm run build
```

Lepas itu restart service supaya `.env` baru dibaca:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-office.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1
```

Nota `TRUSTED_PROXIES`: dibaca guna `env()` dalam `bootstrap/app.php`. **Jangan** `php artisan config:cache`
(env() tak dibaca bila config di-cache) melainkan anda set `TRUSTED_PROXIES` sebagai environment
variable sistem. Bila ia diset, Laravel percaya header `X-Forwarded-For/Host/Proto/Port` supaya
`https` dan IP klien betul. `*` selamat di sini sebab `artisan serve` hanya bind `127.0.0.1`
dan hanya `cloudflared` (lokal) boleh sampai ke situ.

## 7. Hook agent kekal lokal

Hook (`hooks/office-hook.py`) terus hantar ke `http://127.0.0.1:8000/api/ingest`. Jangan tukar ke
`https://office.eadata.my` kerana Access akan halang request tanpa cookie/OTP. Kalau pernah tukar:

```powershell
python hooks\install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes
```

## 8. Nota keselamatan

- **Dua lapisan**: Cloudflare Access (emel OTP) + login Laravel. Jangan matikan salah satu.
- Jangan buka port 8000/8081 di firewall Windows atau router. `artisan serve` bind `127.0.0.1`
  sahaja; semua trafik luar masuk melalui tunnel.
- Rate limit sedia ada: `throttle:login` pada `POST /login`, `throttle:ingest` pada `/api/ingest`
  (lihat `AppServiceProvider`). Boleh tambah Cloudflare WAF rate-limiting rule pada `/login`.
- `APP_DEBUG=false` di produksi supaya stack trace tak bocor.
- `.env`, `<UUID>.json` dan `cert.pem` ialah rahsia. `cert.pem` boleh padam lepas tunnel siap kalau
  tak buat tunnel baru.
- `REVERB_APP_SECRET` hanya untuk server; jangan masuk pembolehubah `VITE_*`.
- Kalau PC sleep/off, tunnel putus. Tetapkan power plan "Never sleep" kalau mahu 24/7.
- Semak berkala siapa dalam policy Access dan sesi aktif (Zero Trust -> Logs -> Access).

## 9. Troubleshooting

| Gejala | Punca biasa | Penyelesaian |
|---|---|---|
| Office hidup tapi tiada update live; console `WebSocket connection to 'wss://office.eadata.my/app/...' failed` | `VITE_REVERB_*` salah / belum `npm run build`; atau rule `/app` tak di atas | Semak `.env` VITE_*, `npm run build`, hard refresh (Ctrl+F5). `cloudflared tunnel ingress rule https://office.eadata.my/app/x` mesti jawab 8081 |
| WS sambung tapi terus tutup / 401 / 403 | Reverb app key tak sepadan; atau sesi Access tamat | Pastikan `REVERB_APP_KEY` sama dengan yang dibake masa build; login Access semula |
| `502 Bad gateway` / Cloudflare error 1033 | `cloudflared` tak connect atau service 8000/8081 mati | `Get-Service cloudflared`; `scripts\start-office.ps1` (lihat jadual health) |
| `419 Page Expired` bila login | Cookie sesi tak dihantar (secure cookie salah) atau proxy header tak dipercayai | `APP_URL=https://office.eadata.my`, `SESSION_SECURE_COOKIE=true`, `TRUSTED_PROXIES=*`; padam cookie, restart; pastikan tiada `config:cache` |
| Mixed content (`blocked: http://` dalam console) | Laravel fikir request `http` sebab `TRUSTED_PROXIES` tak aktif, atau `APP_URL` masih http | Set `TRUSTED_PROXIES=*` & `APP_URL=https://...`, restart serve; build semula |
| Redirect loop ke `http://` selepas login | Sama seperti di atas (scheme salah) | Sama |
| Broadcast event tak sampai (queue OK, tiada error browser) | `REVERB_HOST/PORT/SCHEME` sisi server salah (cuba guna domain awam) | Pastikan `127.0.0.1` / `8081` / `http`; `storage\logs\ops-reverb.err.log` |
| Hook tak sampai / `401` dari ingest | Hook ditunjuk ke domain awam (Access halang) | Pasang semula hook ke `http://127.0.0.1:8000` (bahagian 7) |
| Service cloudflared start tapi tunnel "inactive" | Config / credentials dibaca dari profil `LocalSystem` | Salin config + `<UUID>.json` ke `C:\Windows\System32\config\systemprofile\.cloudflared\` (bahagian 4) |
| Perubahan `.env` tak berkesan | Proses lama masih jalan | `stop-office.ps1` lalu `start-office.ps1` |

Log berguna: `storage\logs\ops-serve.err.log`, `ops-reverb.err.log`, `ops-queue.err.log`,
`ops-schedule.err.log`, `storage\logs\laravel.log`, dan `Get-EventLog`/`cloudflared` service log
(`cloudflared tunnel info office-hub`).

Rujukan lanjut: [windows-services.md](windows-services.md).
