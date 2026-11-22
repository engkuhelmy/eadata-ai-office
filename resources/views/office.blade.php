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
    <script>
        if (new URLSearchParams(location.search).get('tv') === '1') document.documentElement.classList.add('tv');
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
        .map-col { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; align-content: start; }
        .canvas-wrap { position: relative; min-width: 0; }
        #office-canvas { background: #2a2219; border-radius: 8px; overflow: hidden; aspect-ratio: 1440 / 860; width: 100%; }
        /* Tab aras di atas canvas */
        .floor-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
        .floor-tabs button { display: inline-flex; align-items: center; gap: 6px; font-family: inherit; font-size: 13px; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel); color: var(--muted); cursor: pointer; white-space: nowrap; }
        .floor-tabs button:hover { color: var(--text); border-color: var(--accent); }
        .floor-tabs button.active { background: var(--accent); border-color: var(--accent); color: #1d1a17; font-weight: 600; }
        .floor-tabs .n { font-size: 11px; min-width: 18px; text-align: center; padding: 0 6px; border-radius: 999px; background: #1f1b18; color: var(--muted); font-weight: normal; font-variant-numeric: tabular-nums; }
        .floor-tabs button.active .n { background: rgba(29, 26, 23, 0.25); color: #1d1a17; }
        .back-btn { position: absolute; top: 10px; left: 10px; z-index: 3; font-family: inherit; font-size: 12px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--line); background: rgba(42, 37, 33, 0.92); color: var(--text); cursor: pointer; }
        .back-btn:hover { border-color: var(--accent); color: var(--accent); }
        .back-btn[hidden] { display: none; }
        /* Sidebar sentiasa nampak di sebelah peta: melekat di atas dan boleh scroll sendiri bila panjang */
        aside { display: grid; gap: 12px; align-content: start; position: sticky; top: 12px; align-self: start; max-height: calc(100vh - 24px); overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; }
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
        #team details.ended { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 6px; }
        #team details.ended summary { cursor: pointer; color: var(--muted); font-size: 12px; }
        #team .ended-row { opacity: 0.7; }
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
        .nav-link, .head-btn { font-size: 12px; padding: 3px 9px; border: 1px solid var(--line); border-radius: 6px; color: var(--muted); text-decoration: none; background: none; cursor: pointer; font-family: inherit; white-space: nowrap; }
        .nav-link:hover, .head-btn:hover { color: var(--accent); border-color: var(--accent); }
        section.fold { padding: 0; }
        section.fold > summary { cursor: pointer; padding: 10px 12px; font-size: 14px; font-weight: 600; color: var(--accent); list-style: none; display: flex; justify-content: space-between; align-items: center; }
        section.fold > summary::-webkit-details-marker { display: none; }
        section.fold > summary::after { content: '+'; color: var(--muted); }
        section.fold[open] > summary::after { content: '\2212'; }
        section.fold > .fold-body { padding: 0 12px 10px; }
        .filters { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px; }
        .filters select { min-width: 0; padding: 5px 6px; border-radius: 6px; border: 1px solid #4a4238; background: #1f1b18; color: var(--text); font-size: 12px; }
        .warn { color: #f5b841; }
        .plist li { display: grid; grid-template-columns: 10px 1fr auto auto; gap: 8px; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
        .plist li.hv:not(:has(.dot)) { grid-template-columns: 1fr auto; }
        .plist li.dp { grid-template-columns: 1fr 60px auto; }
        .plist .dot { width: 10px; height: 10px; border-radius: 50%; }
        .dp-bar { height: 6px; background: #1f1b18; border-radius: 3px; overflow: hidden; }
        .dp-bar i { display: block; height: 100%; background: var(--accent); }
        .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center; }
        .kpis div { background: #1f1b18; border-radius: 6px; padding: 6px 2px; }
        .kpis b { display: block; font-size: 16px; }
        .kpis span { font-size: 11px; color: var(--muted); }
        .hours { display: flex; align-items: flex-end; gap: 2px; height: 48px; }
        .hours .bar { flex: 1; height: 100%; display: flex; align-items: flex-end; background: #1f1b18; border-radius: 2px; }
        .hours .bar i { display: block; width: 100%; background: var(--sky); border-radius: 2px; }
        .hours-axis { display: flex; justify-content: space-between; margin-top: 2px; }
        .board { display: grid; gap: 8px; }
        .bcol h5 { margin: 0 0 4px; font-size: 12px; }
        .bcol.attention h5 { color: #f5b841; }
        .bcol.doing h5 { color: #10a37f; }
        .bcol.done h5 { color: var(--muted); }
        .bcard { display: grid; width: 100%; text-align: left; gap: 1px; background: #1f1b18; border: 1px solid var(--line); border-radius: 6px; color: var(--text); padding: 5px 8px; margin-bottom: 4px; cursor: pointer; font-family: inherit; font-size: 13px; }
        .bcard:hover { border-color: var(--accent); }
        #alert-bar { position: fixed; top: 8px; left: 50%; transform: translateX(-50%); z-index: 50; display: grid; gap: 6px; width: min(480px, calc(100vw - 16px)); }
        .alert-item { display: flex; align-items: stretch; background: #3a2a14; border: 1px solid #f5b841; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,.5); }
        .alert-item.error { background: #3a1616; border-color: #e53935; }
        .alert-item.rate_limited { background: #1f2630; border-color: #64748b; }
        .alert-open { flex: 1; text-align: left; background: none; border: 0; color: var(--text); padding: 9px 12px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; }
        .alert-close { background: none; border: 0; color: var(--muted); padding: 0 12px; font-size: 20px; cursor: pointer; }
        /* Mod TV: ?tv=1 */
        html.tv body { overflow: hidden; }
        html.tv .head-right, html.tv aside { display: none; }
        html.tv header { position: fixed; top: 0; left: 0; z-index: 5; background: none; border: 0; padding: 8px 12px; }
        html.tv .brand img { width: 44px; height: 30px; }
        html.tv .brand h1 { font-size: 14px; }
        html.tv .brand .by { font-size: 10px; margin-top: 0; }
        html.tv main { position: fixed; inset: 0; padding: 0; display: grid; place-items: center; gap: 0; }
        html.tv #office-canvas { width: min(100vw, calc(100vh * 1440 / 860)); height: auto; border-radius: 0; }
        html.tv .floor-tabs { position: fixed; top: 10px; right: 12px; z-index: 6; }
        html.tv .floor-tabs button { background: rgba(42, 37, 33, 0.85); }
        html.tv .back-btn { display: none; }
        html.tv.tv-idle, html.tv.tv-idle * { cursor: none !important; }
        @media (max-width: 860px) {
            main { grid-template-columns: 1fr; padding: 8px; }
            .brand .by { font-size: 11px; }
            header { flex-wrap: wrap; padding: 8px 10px; }
            .head-right { flex-wrap: wrap; gap: 6px; }
            /* Telefon: tab + peta melekat di atas, panel Team di bawahnya boleh discroll */
            .map-col { position: sticky; top: 0; z-index: 4; background: var(--bg); padding-bottom: 4px; }
            .floor-tabs { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
            .floor-tabs button { padding: 4px 10px; font-size: 12px; }
            aside { position: static; max-height: none; overflow: visible; }
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
            <a class="nav-link" href="/history">Sejarah</a>
            <a class="nav-link" href="/?tv=1">Mod TV</a>
            <button type="button" id="sound-toggle" class="head-btn">Bunyi: on</button>
            <span id="live-status" class="pill polling">Menyambung...</span>
            <form class="logout" method="POST" action="{{ route('logout') }}">
                @csrf
                <button type="submit">Log keluar</button>
            </form>
        </div>
    </header>
    <main>
        <div class="map-col">
            <nav id="floor-tabs" class="floor-tabs" aria-label="Aras bangunan"></nav>
            <div class="canvas-wrap">
                <div id="office-canvas"></div>
                <button type="button" id="back-building" class="back-btn" hidden>&larr; Kembali ke bangunan</button>
            </div>
        </div>
        <aside>
            <details class="fold" open>
                <summary>Team</summary>
                <div class="fold-body">
                    <div class="filters">
                        <select id="flt-pc" aria-label="Tapis ikut PC"><option value="">Semua PC</option></select>
                        <select id="flt-project" aria-label="Tapis ikut projek"><option value="">Semua projek</option></select>
                    </div>
                    <div id="team"></div>
                </div>
            </details>
            <details class="fold" open>
                <summary>Feed live</summary>
                <div class="fold-body"><ul id="feed"></ul></div>
            </details>
            <details class="fold">
                <summary>Sambungan</summary>
                <div class="fold-body" id="panel-health"><p class="muted small">Memuatkan...</p></div>
            </details>
            <details class="fold">
                <summary>Statistik hari ini</summary>
                <div class="fold-body" id="panel-stats"><p class="muted small">Memuatkan...</p></div>
            </details>
            <details class="fold">
                <summary>Papan tugas</summary>
                <div class="fold-body" id="panel-board"><p class="muted small">Memuatkan...</p></div>
            </details>
            <section id="detail">
                <p class="muted">Klik staff (dalam office atau senarai Team) untuk tengok butiran dan tukar nama atau department. Klik satu aras dalam paparan bangunan untuk zoom masuk.</p>
            </section>
        </aside>
    </main>
</body>
</html>
