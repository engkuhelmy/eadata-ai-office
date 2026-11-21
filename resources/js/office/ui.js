import { VENDOR_COLORS } from './layout';
import { getAgent, getEventsFor } from './state';

const STATUS_LABEL = {
    active: 'Kerja',
    idle: 'Standby',
    error: 'Error',
    needs_approval: 'Perlu approval',
    rate_limited: 'Rehat',
    ended: 'Tamat',
};

const STATUS_COLOR = {
    active: '#10a37f',
    idle: '#a89c8c',
    error: '#e53935',
    needs_approval: '#f5b841',
    rate_limited: '#64748b',
    ended: '#6b6257',
};

let selectedId = null;

const esc = (value) =>
    String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[ch]);

const hex = (n) => `#${n.toString(16).padStart(6, '0')}`;

const el = (id) => document.getElementById(id);

export function setStatus(status) {
    const node = el('live-status');
    if (!node) return;
    node.textContent = status === 'live' ? 'Live (WebSocket)' : 'Polling 3s';
    node.className = status === 'live' ? 'pill live' : 'pill polling';
}

export function renderTeam(agents) {
    const node = el('team');
    if (!node) return;

    const groups = {};
    for (const a of agents) {
        const key = a.project || 'Tanpa projek';
        (groups[key] ??= []).push(a);
    }

    const html = Object.keys(groups).sort().map((project) => {
        const rows = groups[project].map((a) => `
            <li data-id="${a.id}" class="row">
                <span class="dot" style="background:${hex(VENDOR_COLORS[a.vendor] ?? 0x64748b)}"></span>
                <span class="name">${esc(a.name)}</span>
                <span class="meta">${esc(a.label)}</span>
                <span class="status" style="color:${STATUS_COLOR[a.status] ?? '#a89c8c'}">${esc(STATUS_LABEL[a.status] ?? a.status)}</span>
                <span class="task">${esc(a.current_task ?? '')}</span>
            </li>`).join('');

        return `<h3>${esc(project)} <span class="count">${groups[project].length}</span></h3><ul>${rows}</ul>`;
    }).join('');

    node.innerHTML = html || '<p class="muted">Tiada agent lagi. Jalankan <code>php artisan office:simulate</code>.</p>';
    node.querySelectorAll('.row').forEach((row) => {
        row.addEventListener('click', () => showDetail(Number(row.dataset.id)));
    });
}

export function renderFeed(events) {
    const node = el('feed');
    if (!node) return;

    node.innerHTML = events.slice(0, 50).map((e) => {
        const time = e.ts ? new Date(e.ts).toLocaleTimeString('ms-MY', { hour12: false }) : '';
        const detail = [e.tool, e.target].filter(Boolean).join(' ');
        return `<li><span class="time">${esc(time)}</span> <strong>${esc(e.agent)}</strong> ${esc(e.event)} <span class="muted">${esc(detail)}</span></li>`;
    }).join('') || '<li class="muted">Belum ada aktiviti.</li>';
}

export function showDetail(id) {
    selectedId = id;
    refreshDetail();
}

export function refreshDetail() {
    const node = el('detail');
    if (!node) return;

    if (selectedId === null) {
        node.innerHTML = '<p class="muted">Klik staff untuk tengok butiran.</p>';
        return;
    }

    const a = getAgent(selectedId);
    if (!a) {
        node.innerHTML = '<p class="muted">Staff ni dah keluar dari office.</p>';
        return;
    }

    const events = getEventsFor(selectedId, 10).map((e) =>
        `<li><span class="time">${esc(e.ts ? new Date(e.ts).toLocaleTimeString('ms-MY', { hour12: false }) : '')}</span> ${esc(e.event)} <span class="muted">${esc([e.tool, e.target].filter(Boolean).join(' '))}</span></li>`
    ).join('');

    node.innerHTML = `
        <h3>${esc(a.name)}</h3>
        <dl>
            <dt>Vendor</dt><dd>${esc(a.label)}</dd>
            <dt>PC</dt><dd>${esc(a.pc ?? '-')}</dd>
            <dt>Projek</dt><dd>${esc(a.project ?? '-')}</dd>
            <dt>Status</dt><dd>${esc(STATUS_LABEL[a.status] ?? a.status)}</dd>
            <dt>Task</dt><dd>${esc(a.current_task ?? '-')}</dd>
        </dl>
        <h4>10 event terakhir</h4>
        <ul class="events">${events || '<li class="muted">Tiada event.</li>'}</ul>`;
}
