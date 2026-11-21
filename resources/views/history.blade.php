<!doctype html>
<html lang="ms">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>Sejarah · AI Office Hub · EA Clouds Technology</title>
    @vite(['resources/js/office/history.js'])
    <style>
        :root { --bg: #1d1a17; --panel: #2a2521; --line: #3a332c; --text: #f5efe6; --muted: #a89c8c; --accent: #d97757; --sky: #78beeb; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); background: linear-gradient(90deg, #2a2219, #1d1a17); }
        .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
        .brand img { width: 64px; height: 44px; image-rendering: pixelated; border-radius: 4px; flex-shrink: 0; }
        .brand h1 { font-size: 20px; margin: 0; line-height: 1.1; }
        .brand .by { display: block; font-size: 12px; color: var(--sky); margin-top: 2px; letter-spacing: 0.6px; text-transform: uppercase; }
        .back { font-size: 12px; padding: 3px 9px; border: 1px solid var(--line); border-radius: 6px; color: var(--muted); text-decoration: none; white-space: nowrap; }
        .back:hover { color: var(--accent); border-color: var(--accent); }
        main { padding: 12px 16px; max-width: 1200px; margin: 0 auto; }
        h2 { font-size: 16px; color: var(--accent); margin: 4px 0 10px; }
        .muted { color: var(--muted); }
        form#h-filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: end; background: var(--panel); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; }
        form#h-filters label { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
        form#h-filters input, form#h-filters select { padding: 7px 8px; border-radius: 6px; border: 1px solid #4a4238; background: #1f1b18; color: var(--text); font-size: 13px; min-width: 130px; }
        button.primary { padding: 8px 16px; border: 0; border-radius: 6px; background: var(--accent); color: #1d1a17; font-weight: 600; cursor: pointer; }
        button.more { margin: 12px auto 0; display: block; padding: 8px 16px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--text); cursor: pointer; }
        button.more[hidden] { display: none; }
        .tablewrap { overflow-x: auto; background: var(--panel); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
        th { color: var(--muted); font-weight: 600; font-size: 12px; white-space: nowrap; }
        td.time { color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
        td.target { word-break: break-all; color: var(--muted); }
        .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
        #h-msg { padding: 10px 2px; font-size: 13px; color: var(--muted); }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <img src="/assets/office/brand_logo.png" alt="EA Clouds Technology">
            <div>
                <h1>AI Office Hub</h1>
                <span class="by">EA Clouds Technology</span>
            </div>
        </div>
        <a class="back" href="/">&larr; Kembali ke office</a>
    </header>
    <main>
        <h2>Sejarah aktiviti</h2>
        <form id="h-filters">
            <label>Tarikh <input type="date" id="f-date"></label>
            <label>Vendor
                <select id="f-vendor">
                    <option value="">Semua</option>
                    <option value="claude">Claude</option>
                    <option value="codex">Codex</option>
                    <option value="hermes">Hermes</option>
                    <option value="antigravity">Antigravity</option>
                    <option value="generic">Lain-lain</option>
                </select>
            </label>
            <label>Projek <input type="text" id="f-project" list="dl-project" placeholder="Semua"></label>
            <label>PC <input type="text" id="f-pc" list="dl-pc" placeholder="Semua"></label>
            <label>Agent
                <select id="f-agent"><option value="">Semua</option></select>
            </label>
            <button type="submit" class="primary">Tapis</button>
            <datalist id="dl-project"></datalist>
            <datalist id="dl-pc"></datalist>
        </form>
        <div class="tablewrap">
            <table>
                <thead>
                    <tr><th>Masa</th><th>Agent</th><th>Vendor</th><th>Event</th><th>Tool</th><th>Sasaran</th><th>Department</th></tr>
                </thead>
                <tbody id="h-body"></tbody>
            </table>
        </div>
        <p id="h-msg"></p>
        <button type="button" id="h-more" class="more" hidden>Muat lebih</button>
    </main>
</body>
</html>
