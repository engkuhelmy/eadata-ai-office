# AI Office Hub: Build Brief untuk Claude Code

> Brief lengkap. Baca semua dulu, kemudian buat **Plan** sebelum tulis kod.
> Bahasa komunikasi: Bahasa Malaysia santai + istilah teknikal English.

---

## 1. Apa kita bina

Satu **virtual office isometric pixel art (2.5D)** dalam browser yang tunjuk semua AI agent dalam PC aku sebagai "staff".

- Setiap agent session = seorang staff (avatar pixel).
- Bila agent buat kerja, staff **jalan ke meja department** ikut jenis kerja (Frontend, Backend, QA, Deploy, Research, Ops, Meeting, Kanban).
- Bubble atas kepala tunjuk task semasa (cth. "Editing navbar.vue", "Running pytest").
- Warna baju ikut vendor. Label tunjuk vendor + nama PC.
- Agent dalam **folder projek yang sama = satu team**, walaupun lain vendor.
- Side panel: activity feed live + senarai team.

Rujukan visual: office isometric warm lighting, meja dengan CRT monitor, rak buku, whiteboard chart, pokok, lantai checker, speech bubble putih (gaya "Fetching web content", "Processing Data", "Analyzing Results").

### Vendor yang wajib disokong (semua dalam satu PC Ubuntu)

| Vendor | Agent | Cara tangkap event |
|---|---|---|
| Anthropic | **Claude Code** | hooks dalam `~/.claude/settings.json` |
| OpenAI | **Codex CLI** | hooks dalam `~/.codex/hooks.json` (user perlu trust melalui `/hooks`); fallback legacy `notify` dalam `~/.codex/config.toml` |
| Nous Research | **Hermes Agent** | shell hooks dalam `~/.hermes/config.yaml` |
| Lain-lain | CrewAI, n8n, skrip sendiri | `POST /api/ingest?src=generic` (JSON ringkas) |

Extensible: Gemini CLI / Antigravity boleh ditambah kemudian guna pola adapter yang sama.

---

## 2. Keputusan seni bina (jangan ubah tanpa tanya)

- **Backend:** Laravel 12 (PHP 8.3)
- **Realtime:** Laravel Reverb (WebSocket) + **fallback polling** `/office/state` setiap 3s
- **Frontend office:** Phaser 3 (isometric), dibundle dengan Vite
- **DB:** SQLite untuk MVP lokal (boleh tukar MySQL kemudian)
- **Queue:** database driver
- **Hosting MVP:** jalan **dalam PC sendiri** (`localhost:8000`). Akses dari luar melalui **Cloudflare Tunnel + Cloudflare Access** ke `eadata.my`. VPS hanya bila ada PC kedua.
- **Auth:** Laravel login (session) + rate limit. Ingest guna **device token** (Bearer, disimpan sha256 dalam DB).

### Aliran data

```
Agent hook (Claude Code / Codex / Hermes)
  → office-hook (Python, baca stdin, redact, fork ke background, return < 100ms, spool bila offline)
  → POST http://127.0.0.1:8000/api/ingest?src=<vendor>&event=<nama>   (Bearer eod_xxx)
  → Adapter per vendor → NormalizedEvent → DepartmentRouter
  → Queue job ProcessAgentEvent → DB (agents, agent_events) → broadcast Reverb
     (private channel `office`, event `.agent.updated`)
  → Browser: Phaser office update live
```

---

## 3. Struktur cadangan

```
app/
  Office/
    NormalizedEvent.php          # DTO: vendor, agent_id, session_id, name, label, pc,
                                 #      project, event, tool, target, department, ts
    DepartmentRouter.php         # teka department dari tool/target/command
    Redactor.php                 # mask secret (API key, token, password, .env content)
    Adapters/
      AdapterInterface.php
      ClaudeCodeAdapter.php
      CodexAdapter.php
      HermesAdapter.php
      GenericAdapter.php
    AdapterRegistry.php
  Http/Controllers/
    IngestController.php         # POST /api/ingest
    OfficeController.php         # GET / (office), GET /office/state
  Jobs/ProcessAgentEvent.php
  Events/AgentUpdated.php        # ShouldBroadcast → private-office
  Models/{Device,Agent,AgentEvent}.php
  Console/Commands/
    OfficeUser.php               # office:user {email} --role=owner|viewer
    OfficeDevice.php             # office:device {name} | --revoke=ID  (print token sekali)
    OfficeSimulate.php           # office:simulate (team 5 agent, 3 vendor + generic)
database/migrations/             # users.role, devices, agents, agent_events
resources/js/office/             # Phaser scenes, sprites, pathfinding grid
public/assets/office/            # tileset + sprite (placeholder dulu)
hooks/
  office-hook                    # Python 3, tiada dependency luar
  install-hooks.py               # --url --token --tools claude,codex,hermes | --uninstall
tests/
  Unit/OfficeAdaptersTest.php
  Feature/IngestTest.php
  Feature/AuthTest.php
  fixtures/{claude,codex,hermes}/*.json
```

---

## 4. Event standard (NormalizedEvent.event)

`session_start, prompt, tool_start, tool_end, tool_error, needs_approval, subagent_start, subagent_stop, turn_done, idle, rate_limited, error, compact, session_end`

### Lokasi dalam office

| Keadaan | Staff pergi ke |
|---|---|
| session_start | Pintu (clock in) |
| prompt | Kanban board |
| edit `.vue .tsx .jsx .css .scss .html .blade.php` | Frontend |
| edit `.php .py .go .rs .js(server) routes/ api/ app/` | Backend |
| test (`phpunit pest jest vitest pytest`) atau fail dalam `tests/` | QA |
| `git push`, `docker`, `ssh`, `pm2`, `deploy`, `rsync`, `kubectl` | Deploy |
| read / grep / glob / web search / web fetch | Research |
| MCP tool, command lain | Ops / Server room |
| subagent_start / delegate | Bilik Meeting |
| needs_approval | Loceng approval (staff angkat tangan) |
| rate_limited | Mesin kopi |
| idle / turn_done (lama > 2 min) | Water cooler |
| error / tool_error | kekal di meja, skrin bertukar merah |
| session_end | keluar ikut pintu, hilang lepas 10s |

Kalau payload ada `department` eksplisit (generic), guna terus.

---

## 5. Spesifikasi adapter

### 5.1 Claude Code (`src=claude`)
Hook events: `SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Notification, SubagentStop, Stop, SessionEnd` (+ `SubagentStart` kalau versi ada).
Stdin JSON ada `session_id, cwd, hook_event_name, tool_name, tool_input, prompt, ...`.
- `tool_input.file_path` → target untuk Edit/Write/Read
- `tool_input.command` → target untuk Bash
- `Task` / `Agent` tool → subagent_start
- `Notification` dengan mesej permission → needs_approval
- Hook mesti `"async": true` supaya tak lambatkan agent.

Contoh config yang install-hooks.py tulis (merge, jangan overwrite):
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "*", "hooks": [
        { "type": "command", "command": "~/.office-hub/office-hook --src claude", "async": true }
      ]}
    ]
  }
}
```
Ulang untuk setiap event di atas.

### 5.2 Codex (`src=codex`)
- Semak format `~/.codex/hooks.json` ikut versi Codex yang terpasang (`codex --version`, docs rasmi). **Jangan teka** schema; kalau tak pasti, baca docs/`codex --help` dulu.
- Lepas install, user perlu buka `codex` → `/hooks` → trust hook office-hub. install-hooks.py mesti print arahan ni.
- Fallback: legacy `notify = ["~/.office-hub/office-hook", "--src", "codex", "--legacy-notify"]` dalam `~/.codex/config.toml` (hanya bagi `turn_done`).

### 5.3 Hermes Agent (`src=hermes`) — BARU
Shell hooks dalam `~/.hermes/config.yaml`:
```yaml
hooks:
  on_session_start:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  pre_llm_call:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  pre_tool_call:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  post_tool_call:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  subagent_start:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  subagent_stop:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
  on_session_end:
    - command: "~/.office-hub/office-hook --src hermes"
      timeout: 5
```
Stdin JSON:
```json
{
  "hook_event_name": "pre_tool_call",
  "tool_name": "terminal",
  "tool_input": {"command": "pytest -q"},
  "session_id": "sess_abc123",
  "cwd": "/home/helmy/projek/eadata-web",
  "profile": "default",
  "extra": {"task_id": "...", "tool_call_id": "..."}
}
```
`tool_name` dan `tool_input` = null untuk event bukan tool.

Mapping:
- `on_session_start` → session_start
- `pre_llm_call` → prompt (**sekali per turn sahaja**; abaikan pre_llm_call berikutnya dalam turn yang sama, guna state per session_id)
- `pre_tool_call` → tool_start; `post_tool_call` → tool_end (atau tool_error kalau extra tunjuk gagal)
- `subagent_start` / `subagent_stop` → subagent_*
- `on_session_end` → session_end (kalau `extra.interrupted` = true → idle)
- `project` = basename(cwd); `agent label` = "Hermes" + profile kalau bukan default
- Tool → department: `write_file`, `patch`, `read_file` → ikut extension path; `terminal` → ikut `tool_input.command`; `delegate_task` → Meeting; tool web/browser/search → Research; lain → Ops. Semak nama tool sebenar dengan `hermes tools` / docs dan update mapping.

**PERANGKAP WAJIB (Hermes baca stdout hook sebagai arahan):**
- `office-hook` **tidak boleh print apa-apa ke stdout** dan **mesti sentiasa exit 0**. Stdout `{"decision":"block"}` boleh block tool, `{"context": ...}` pada pre_llm_call akan inject ke prompt, exit code 2 block pre_tool_call.
- **Jangan** letak `fail_closed`.
- Kali pertama, Hermes minta user approve setiap (event, command) dan simpan dalam `~/.hermes/shell-hooks-allowlist.json`. install-hooks.py mesti beritahu user.
- Test: `hermes hooks list`, `hermes hooks test pre_tool_call`.
- install-hooks.py mesti **merge YAML** (guna parser YAML minimal atau PyYAML kalau ada; kalau tiada, append block dengan marker `# office-hub:begin` / `# office-hub:end` supaya uninstall bersih). Backup `config.yaml.bak-office`.

### 5.4 Generic (`src=generic`)
```json
{"agent":"researcher-1","name":"Rafiq","label":"CrewAI","event":"tool_start",
 "tool":"web_search","target":"harga VPS Malaysia","project":"eadata-web","department":"research"}
```

---

## 6. office-hook (Python, PC side)

- Baca stdin + argumen `--src`, tambah `pc` (hostname) dan `ts`.
- **Redact di PC:** buang isi fail (`content`, `new_string`, `old_string`, `patch` body), simpan path sahaja; mask pattern secret (`sk-…`, `ghp_…`, `AKIA…`, `Bearer …`, `password=…`, baris dari `.env`). Potong target > 200 aksara.
- **Fork ke background** (`os.fork` + `setsid`) dan return segera (< 100ms). Parent: tiada output, exit 0.
- Child: POST ke URL dalam `~/.office-hub/config.json` (`url`, `token`), timeout 3s.
- Gagal → append ke `~/.office-hub/spool.jsonl`; setiap panggilan berjaya, flush spool secara batch (max 100).
- Tiada dependency luar (stdlib `urllib` sahaja).
- Log error ke `~/.office-hub/hook.log` (rotate 1MB), bukan stdout/stderr.

---

## 7. Server side

- `POST /api/ingest`: Bearer token → cari device (sha256), 401 kalau salah. Rate limit 120/min per device. Validate `src` ada dalam registry. Return **202** segera, dispatch job.
- `Redactor` lapis kedua di server. **Raw payload tidak disimpan**; simpan NormalizedEvent sahaja.
- `ProcessAgentEvent`: upsert `agents` (key: vendor + session_id), insert `agent_events`, kira department, broadcast `AgentUpdated`.
- Agent tanpa event > 10 min → auto idle; > 60 min → auto session_end (scheduled command).
- `GET /office/state`: semua agent aktif + 50 event terakhir (untuk reload page & fallback polling).
- Web routes di belakang `auth`. `/login` rate limit 5 cubaan / 5 minit.
- `/?demo=1`: frontend jalan dengan data palsu tanpa backend (untuk kerja grafik).

---

## 8. Frontend (Phaser 3)

- Grid isometric (cth. 20×14 tile), layout department tetap dengan label kecil.
- Pathfinding grid (EasyStar.js atau A* ringkas) supaya staff jalan elak meja.
- Sprite staff: placeholder (bulatan + badan warna vendor) dulu; struktur siap untuk spritesheet 4 arah (idle, walk, typing).
- Warna vendor: Claude `#D97757` (oren), Codex `#10A37F` (hijau), Hermes `#8B5CF6` (ungu), Generic `#64748B` (kelabu).
- Bubble task (putih, teks pendek), skrin meja merah bila error, ikon loceng bila needs_approval.
- Klik staff → panel detail (vendor, PC, project, 10 event terakhir).
- Side panel: feed live + team (group ikut project).
- Lighting hangat (overlay gradient), gaya rujukan di bahagian 1. Aset sebenar boleh guna pack isometric office dari itch.io kemudian; **jangan habiskan masa pada art sebelum Fasa C lulus**.

---

## 9. Fasa kerja & Definition of Done

### Fasa A: Laravel jalan (lokal, SQLite)
- [ ] Projek Laravel + Reverb (`php artisan install:broadcasting`) + migration
- [ ] Adapter 4 vendor + unit test dengan fixture (`tests/fixtures/{claude,codex,hermes}`)
- [ ] Feature test: ingest tanpa token = 401; token + payload = 202 + row wujud (queue sync)
- [ ] Feature test: login betul/salah, rate limit, guest redirect ke `/login`
- [ ] `office:user`, `office:device`, `office:simulate` jalan

### Fasa B: Office live
- [ ] `office:simulate` → staff bergerak dalam browser (bukan demo)
- [ ] Reverb private channel `office` berfungsi; fallback polling bila WS gagal
- [ ] Reload page pulihkan state

### Fasa C: Agent sebenar dalam PC
- [ ] `install-hooks.py --tools claude,codex,hermes` (backup, merge, uninstall bersih)
- [ ] Claude Code sebenar → staff ke Frontend/Backend/QA ikut tool
- [ ] Codex sebenar → muncul (selepas trust `/hooks`)
- [ ] Hermes sebenar → muncul; `hermes hooks test` lulus; agent tak jadi lambat atau terblock
- [ ] Simpan payload sebenar setiap vendor sebagai fixture baru
- [ ] Offline spool: matikan server, buat kerja, hidupkan, event sampai

### Fasa D: Akses dari luar (tanpa VPS)
- [ ] Dokumen `docs/cloudflare-tunnel.md`: `cloudflared tunnel create office-hub`, route DNS `eadata.my` → `http://localhost:8000`, termasuk path WebSocket Reverb, `cloudflared service install`
- [ ] Cloudflare Access (email OTP) untuk seluruh domain. Hook kekal ke `127.0.0.1`, jadi tiada bypass diperlukan
- [ ] Supervisor/systemd unit untuk `serve`/`octane`, `reverb:start`, `queue:work`, `schedule:work`
- [ ] Login dari PC/phone lain berjaya

**Definition of Done:** Dalam satu folder projek, Claude Code + Codex + Hermes buat kerja serentak → tiga staff (warna berbeza) muncul sebagai **satu team**, bergerak ke department betul, dan aku boleh tengok live dari `https://eadata.my` selepas login.

---

## 10. Peraturan kerja untuk Claude Code

1. Mula dengan **Plan**: senarai fail + urutan. Tunggu aku approve.
2. Kalau dalam repo dah ada overlay Fasa 1 (adapter, office-hook, install-hooks.py), **guna semula dan betulkan**, jangan tulis semula dari kosong.
3. Jangan teka schema hook vendor. Kalau tak pasti (terutama Codex), semak versi terpasang dan docs, kemudian tulis fixture dari payload sebenar.
4. Tulis test dulu untuk adapter dan ingest. `php artisan test` mesti hijau sebelum pindah fasa.
5. Jangan sentuh config agent sebenar aku (`~/.claude`, `~/.codex`, `~/.hermes`) tanpa minta izin; install-hooks.py ada `--dry-run` yang tunjuk diff dulu.
6. Keselamatan: isi fail tak pernah dihantar, raw payload tak disimpan, tiada endpoint yang jalankan bash dari web.
7. Lepas setiap fasa: ringkasan pendek + command untuk aku uji sendiri.

---

## 11. Selepas MVP (jangan buat sekarang, cuma reka supaya senang tambah)

- Hermes sebagai **Office Manager**: aku mesej Hermes di Telegram → dia delegate ke Claude Code / Codex (`claude -p`, `codex exec`) dalam folder projek → office tunjuk Hermes jalan ke meja agent tu (Meeting) sebelum kerja bermula.
- Token & kos per agent (tail transcript JSONL).
- Kanban auto dari prompt, token spike alert.
- Sokongan Gemini CLI & Antigravity.
- Pindah ke VPS bila ada PC kedua (tukar URL dalam `~/.office-hub/config.json` sahaja).
