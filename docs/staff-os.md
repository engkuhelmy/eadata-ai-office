# Staff OS: staf AI sebenar dalam office

Staf sebenar (Mira, Zara, Anna, Mary, Hana, Elizabeth, Mila, Anabell, Mas Elon, Sam, Adriana, Bill, Ayu, Nia) didaftar dari fail MD Staff OS. Mereka sentiasa ada dalam senarai Team. Bila belum check in atau dah habis kerja, mereka ditanda **Off**, tak muncul di peta, dan sweep tak pernah tamatkan mereka.

## Pasang / kemas kini

1. Letak fail MD (satu fail setiap staf + `README.md`) dalam `storage/app/private/staff-os/`. Folder ni tak masuk git.
2. Import:

```bash
php artisan office:staff-import            # atau: php artisan office:staff-import /path/folder
php artisan office:staff-import --deactivate-missing   # staf yang tiada lagi dalam folder = tidak aktif
```

Import kemas kini profil (jawatan, unit, lapor kepada, team, skop, handoff, brief penuh) tanpa ganggu staf yang sedang bekerja. Gaya watak yang owner tukar tidak ditimpa.

## Meja tetap

Ditetapkan dalam `config/staff.php` (`placements`):

| Aras | Staf | Meja |
|---|---|---|
| L3 | Mira | HOD (dekat CEO) |
| L3 | Mary | CFO |
| L2 | Hana, Anna | Head Office |
| L2 | Zara, Anabell | Sales |
| L2 | Mila, Ayu, Nia | Marketing |
| L2 | Adriana | IT Backend |
| L2 | Bill | IT Ops |
| L1 | Elizabeth, Mas Elon | Training Room |
| L1 | Sam | Client Space |

Bila staf hantar event tanpa `department`, office pilih bilik ikut aturan ini:

- Check in, `prompt`, `tool_start` dan `tool_end`: meja tetap.
- Tool `handoff`, `meeting`, `task`, `agent` atau `delegate_task`, dan `subagent_*`: Big Meeting Room (L3).
- `needs_approval`: Approval (L2). `rate_limited`: Coffee.
- `session_end`: staf berjalan keluar ikut pintu dan ditanda Off.

Kalau payload hantar `department` yang sah, office sentiasa ikut department itu.

## Check in (wajib sebelum mula kerja)

```bash
curl -X POST "https://<office>/api/staff/checkin" \
  -H "Authorization: Bearer eod_xxx" -H "Content-Type: application/json" \
  -d '{"agent":"zara"}'
```

Balasan `200` mengandungi:

- `staff`: nama, jawatan, unit, lapor kepada, team, fasa, meja.
- `scope.buat` dan `scope.tak_boleh_buat`.
- `handoffs`.
- `rules`: peraturan wajib dari README.
- `handoff_format`.
- `workflow`: langkah kerja.
- `ingest`: URL dan contoh event.
- `brief_markdown`: fail MD penuh.

AI staf mesti baca brief ini sebelum mula kerja. Selepas check in, staf berjalan dari pintu ke meja tetap, dan panel profil dalam office menunjukkan bila brief diterima.

Ralat yang mungkin keluar:

- `404 unknown_staff`: agent tak berdaftar. Jangan mula kerja; tanya Mira.
- `403 inactive`: staf dinyahaktif.
- `401`: token device salah.

## Semasa bekerja

Guna `POST /api/ingest?src=generic`, format generic yang sama. Untuk staf, `name`, `label` dan `project` diisi automatik:

```json
{"agent":"zara","event":"tool_start","tool":"generate_report","target":"GMV harian"}
{"agent":"zara","event":"tool_end","tool":"generate_report","target":"SIAP: dashboard dikemas kini"}
{"agent":"zara","event":"tool_start","tool":"handoff","target":"Fees bulanan kepada Mary"}
{"agent":"zara","event":"needs_approval","tool":"bayaran host"}
{"agent":"zara","event":"session_end"}
```

Jangan letak PII (e-mel, no. telefon, IC, akaun bank) dalam `target`. Staf yang senyap 60 minit ditanda Off di meja tetap.
