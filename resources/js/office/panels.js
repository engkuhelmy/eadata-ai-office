// Panel sisi: Sambungan, Statistik hari ini, Papan tugas. Poll /office/insights setiap 10s.
import { DEPARTMENTS, VENDOR_COLORS } from './layout';
import { esc, hex, fmtNum, relTime, getJson } from './util';

const POLL_MS = 10000;
const STALE_MS = 30 * 60 * 1000;
const NA = '<p class="muted small">Data tidak tersedia.</p>';

let openAgent = () => {};

const $ = (id) => document.getElementById(id);

function renderHealth(health) {
    const node = $('panel-health');
    if (!node) return;
    if (!health) { node.innerHTML = NA; return; }

    const vendors = (health.vendors ?? []).map((v) => {
        const last = v.last_event_at ? new Date(v.last_event_at).getTime() : null;
        const stale = Number(v.agents) > 0 && (last === null || Date.now() - last > STALE_MS);
        return `<li class="hv">
            <span class="dot" style="background:${hex(VENDOR_COLORS[v.vendor] ?? 0x64748b)}"></span>
            <span class="hv-name">${esc(v.label ?? v.vendor)}</span>
            <span class="muted small">${esc(v.agents ?? 0)} agent</span>
            <span class="small ${stale ? 'warn' : 'muted'}">${stale ? '&#9888; ' : ''}${esc(relTime(v.last_event_at))}</span>
        </li>`;
    }).join('');

    const devices = (health.devices ?? []).map((d) => `<li class="hv">
            <span class="hv-name">${esc(d.name)}${d.revoked ? ' <span class="pin">dibatal</span>' : ''}</span>
            <span class="muted small">${esc(relTime(d.last_used_at))}</span>
        </li>`).join('');

    node.innerHTML = `<ul class="plist">${vendors || '<li class="muted small">Tiada vendor.</li>'}</ul>
        <h4>Peranti</h4>
        <ul class="plist">${devices || '<li class="muted small">Tiada peranti.</li>'}</ul>`;
}

function renderStats(stats) {
    const node = $('panel-stats');
    if (!node) return;
    const today = stats?.today;
    if (!today) { node.innerHTML = NA; return; }

    const hourly = Array.isArray(stats.hourly) ? stats.hourly : [];
    const max = Math.max(1, ...hourly.map((h) => Number(h.events) || 0));
    const bars = hourly.map((h) => {
        const pct = Math.round(((Number(h.events) || 0) / max) * 100);
        return `<span class="bar" title="${esc(h.hour)}:00 - ${esc(h.events)} event"><i style="height:${Math.max(pct, h.events ? 4 : 0)}%"></i></span>`;
    }).join('');

    const depts = Object.entries(today.by_department ?? {})
        .sort((a, b) => b[1] - a[1]).slice(0, 5);
    const topMax = Math.max(1, ...depts.map(([, n]) => n));
    const deptRows = depts.map(([key, n]) => `<li class="dp">
            <span class="small">${esc(DEPARTMENTS[key]?.label ?? key)}</span>
            <span class="dp-bar"><i style="width:${Math.round((n / topMax) * 100)}%"></i></span>
            <span class="small muted">${esc(fmtNum(n))}</span>
        </li>`).join('');

    node.innerHTML = `
        <div class="kpis">
            <div><b>${esc(fmtNum(today.events))}</b><span>Event</span></div>
            <div><b class="${today.errors ? 'warn' : ''}">${esc(fmtNum(today.errors))}</b><span>Error</span></div>
            <div><b>${esc(fmtNum(today.active_agents))}</b><span>Agent aktif</span></div>
        </div>
        <h4>Event ikut jam</h4>
        <div class="hours">${bars}</div>
        <div class="hours-axis small muted"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>
        <h4>Department teratas</h4>
        <ul class="plist">${deptRows || '<li class="muted small">Belum ada data.</li>'}</ul>`;
}

function renderBoard(board) {
    const node = $('panel-board');
    if (!node) return;
    if (!board) { node.innerHTML = NA; return; }

    const col = (title, list, cls) => `<div class="bcol ${cls}">
        <h5>${esc(title)} <span class="count">${(list ?? []).length}</span></h5>
        ${(list ?? []).slice(0, 15).map((a) => `<button type="button" class="bcard" data-id="${esc(a.id)}">
            <strong>${esc(a.name)}</strong>
            <span class="muted small">${esc(a.project ?? '')}</span>
            ${a.current_task ? `<span class="small">${esc(a.current_task)}</span>` : ''}
        </button>`).join('') || '<span class="muted small">-</span>'}
    </div>`;

    node.innerHTML = `<div class="board">
        ${col('Doing', board.doing, 'doing')}
        ${col('Perlu perhatian', board.attention, 'attention')}
        ${col('Selesai', board.done, 'done')}
    </div>`;
    node.querySelectorAll('.bcard').forEach((b) => {
        b.addEventListener('click', () => openAgent(Number(b.dataset.id)));
    });
}

async function refresh() {
    if (document.hidden) return;
    try {
        const data = await getJson('/office/insights');
        renderHealth(data.health);
        renderStats(data.stats);
        renderBoard(data.board);
    } catch {
        ['panel-health', 'panel-stats', 'panel-board'].forEach((id) => {
            const node = $(id);
            if (node && !node.dataset.ok) node.innerHTML = NA;
        });
        return;
    }
    ['panel-health', 'panel-stats', 'panel-board'].forEach((id) => {
        const node = $(id);
        if (node) node.dataset.ok = '1';
    });
}

export function initPanels({ onOpenAgent } = {}) {
    if (onOpenAgent) openAgent = onOpenAgent;
    if (!$('panel-health')) return;
    refresh();
    setInterval(refresh, POLL_MS);
}
