<!doctype html>
<html lang="ms">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Office Hub</title>
    @vite(['resources/js/office/main.js'])
    <style>
        :root { --bg: #1d1a17; --panel: #2a2521; --line: #3a332c; --text: #f5efe6; --muted: #a89c8c; --accent: #d97757; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid var(--line); }
        header h1 { font-size: 18px; margin: 0; }
        .pill { font-size: 12px; padding: 3px 8px; border-radius: 999px; background: var(--panel); }
        .pill.live { color: #10a37f; }
        .pill.polling { color: #f5b841; }
        .muted { color: var(--muted); }
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
        .events li { font-size: 12px; padding: 3px 0; border-bottom: 1px solid var(--line); }
        @media (max-width: 860px) {
            main { grid-template-columns: 1fr; padding: 8px; }
        }
    </style>
</head>
<body>
    <header>
        <h1>AI Office Hub</h1>
        <span id="live-status" class="pill polling">Menyambung...</span>
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
                <p class="muted">Klik staff untuk tengok butiran.</p>
            </section>
        </aside>
    </main>
</body>
</html>
