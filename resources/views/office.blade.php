<!doctype html>
<html lang="ms">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>AI Office Hub · EA Clouds Technology</title>
    <script>
        window.OFFICE = {
            canEdit: @json($canEdit),
            departments: @json($departments),
            csrf: @json(csrf_token()),
        };
    </script>
    @vite(['resources/js/office/main.js'])
    <style>
        :root { --bg: #1d1a17; --panel: #2a2521; --line: #3a332c; --text: #f5efe6; --muted: #a89c8c; --accent: #d97757; --sky: #78beeb; --navy: #183678; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); background: linear-gradient(90deg, #2a2219, #1d1a17); }
        .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
        .brand img { width: 64px; height: 44px; image-rendering: pixelated; border-radius: 4px; flex-shrink: 0; }
        .brand h1 { font-size: 20px; margin: 0; line-height: 1.1; letter-spacing: 0.2px; }
        .brand .by { display: block; font-size: 12px; color: var(--sky); margin-top: 2px; letter-spacing: 0.6px; text-transform: uppercase; }
        .head-right { display: flex; align-items: center; gap: 10px; }
        .pill { font-size: 12px; padding: 3px 8px; border-radius: 999px; background: var(--panel); white-space: nowrap; }
        .pill.live { color: #10a37f; }
        .pill.polling { color: #f5b841; }
        .logout button { background: none; border: 1px solid var(--line); color: var(--muted); border-radius: 6px; padding: 3px 8px; cursor: pointer; font-size: 12px; }
        .muted { color: var(--muted); }
        .small { font-size: 12px; }
        main { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 12px; padding: 12px; }
        #office-canvas { background: #2a2219; border-radius: 8px; overflow: hidden; aspect-ratio: 1280 / 720; width: 100%; }
        aside { display: grid; gap: 12px; align-content: start; }
        section { background: var(--panel); border-radius: 8px; padding: 10px 12px; }
        section h2 { font-size: 14px; margin: 0 0 8px; color: var(--accent); }
        h3 { font-size: 13px; margin: 10px 0 4px; }
        h4 { font-size: 12px; margin: 10px 0 4px; color: var(--muted); }
        .count { color: var(--muted); font-weight: normal; }
        ul { list-style: none; margin: 0; padding: 0; }
        #team .row { display: grid; grid-template-columns: 10px 1fr auto; gap: 2px 8px; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--line); font-size: 13px; cursor: pointer; }
        #team .row:hover .name { color: var(--accent); }
        #team .row .dot { width: 10px; height: 10px; border-radius: 50%; grid-row: span 2; }
        #team .row .meta { display: none; }
        #team .row .task { grid-column: 2 / 4; color: var(--muted); font-size: 12px; }
        #team .row .status { font-size: 12px; }
        #feed { max-height: 260px; overflow: auto; font-size: 12px; }
        #feed li { padding: 3px 0; border-bottom: 1px solid var(--line); }
        .time { color: var(--muted); font-variant-numeric: tabular-nums; }
        #detail dl { display: grid; grid-template-columns: auto 1fr; gap: 3px 10px; font-size: 13px; margin: 0; }
        #detail dt { color: var(--muted); }
        #detail dd { margin: 0; }
        .pin { font-size: 11px; color: var(--sky); border: 1px solid var(--sky); border-radius: 999px; padding: 0 6px; margin-left: 4px; }
        form.edit { display: grid; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
        form.edit label { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
        form.edit input, form.edit select { padding: 7px 8px; border-radius: 6px; border: 1px solid #4a4238; background: #1f1b18; color: var(--text); font-size: 13px; }
        form.edit .actions { display: flex; align-items: center; gap: 10px; }
        form.edit button { padding: 7px 14px; border: 0; border-radius: 6px; background: var(--accent); color: #1d1a17; font-weight: 600; cursor: pointer; }
        .events li { font-size: 12px; padding: 3px 0; border-bottom: 1px solid var(--line); }
        @media (max-width: 860px) {
            main { grid-template-columns: 1fr; padding: 8px; }
            .brand .by { font-size: 11px; }
        }
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
        <div class="head-right">
            <span id="live-status" class="pill polling">Menyambung...</span>
            <form class="logout" method="POST" action="{{ route('logout') }}">
                @csrf
                <button type="submit">Log keluar</button>
            </form>
        </div>
    </header>
    <main>
        <div id="office-canvas"></div>
        <aside>
            <section>
                <h2>Team</h2>
                <div id="team"></div>
            </section>
            <section>
                <h2>Feed live</h2>
                <ul id="feed"></ul>
            </section>
            <section id="detail">
                <p class="muted">Klik staff (dalam office atau senarai Team) untuk tengok butiran dan tukar nama atau department.</p>
            </section>
        </aside>
    </main>
</body>
</html>
