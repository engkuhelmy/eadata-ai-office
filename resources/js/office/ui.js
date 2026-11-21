import { DEPARTMENTS, VENDOR_COLORS } from './layout';
import { applyBroadcast, getAgent, getEventsFor } from './state';

// Dari Blade: { canEdit, departments, csrf }
const CONFIG = window.OFFICE ?? { canEdit: false, departments: [], csrf: '' };

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
                <span class="task">${esc(DEPARTMENTS[a.department]?.label ?? '')}${a.current_task ? ' · ' + esc(a.current_task) : ''}</span>
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

export function deptLabel(key) {
    if (!key) return '-';
    const dept = DEPARTMENTS[key];
    return dept ? `${dept.label} (${key})` : key;
}

export function showDetail(id) {
    selectedId = id;
    buildDetail();
    refreshDetail();
}

// Bina struktur panel sekali bila pilihan berubah, supaya form tak hilang bila data refresh
function buildDetail() {
    const node = el('detail');
    if (!node) return;

    const a = selectedId !== null ? getAgent(selectedId) : null;
    if (!a) return;

    const options = CONFIG.departments
        .map((k) => `<option value="${esc(k)}" ${a.pinned_department === k ? 'selected' : ''}>${esc(deptLabel(k))}</option>`)
        .join('');

    const form = CONFIG.canEdit ? `
        <form id="detail-form" class="edit">
            <label>Nama paparan
                <input name="name" maxlength="100" placeholder="${esc(a.auto_name ?? '')}" value="${esc(a.custom_name ?? '')}">
            </label>
            <label>Department
                <select name="department"><option value="">Auto (ikut kerja)</option>${options}</select>
            </label>
            <div class="actions"><button type="submit">Simpan</button><span id="detail-msg" class="muted"></span></div>
        </form>` : '<p class="muted small">Hanya owner boleh tukar nama dan department.</p>';

    node.innerHTML = `
        <h3 id="detail-title"></h3>
        <dl id="detail-info"></dl>
        ${form}
        <h4>10 event terakhir</h4>
        <ul id="detail-events" class="events"></ul>`;

    node.querySelector('#detail-form')?.addEventListener('submit', saveDetail);
}

export function refreshDetail() {
    const node = el('detail');
    if (!node) return;

    if (selectedId === null) return;

    const a = getAgent(selectedId);
    if (!a) {
        node.innerHTML = '<p class="muted">Staff ni dah keluar dari office.</p>';
        return;
    }
    if (!el('detail-info')) buildDetail();

    el('detail-title').textContent = a.name ?? '';
    el('detail-info').innerHTML = `
        <dt>Vendor</dt><dd>${esc(a.label)}</dd>
        <dt>PC</dt><dd>${esc(a.pc ?? '-')}</dd>
        <dt>Projek</dt><dd>${esc(a.project ?? '-')}</dd>
        <dt>Department</dt><dd>${esc(deptLabel(a.department))}${a.pinned_department ? ' <span class="pin">dipin</span>' : ''}</dd>
        <dt>Status</dt><dd>${esc(STATUS_LABEL[a.status] ?? a.status)}</dd>
        <dt>Task</dt><dd>${esc(a.current_task ?? '-')}</dd>`;

    const events = getEventsFor(selectedId, 10).map((e) =>
        `<li><span class="time">${esc(e.ts ? new Date(e.ts).toLocaleTimeString('ms-MY', { hour12: false }) : '')}</span> ${esc(e.event)} <span class="muted">${esc([e.tool, e.target].filter(Boolean).join(' '))}</span></li>`
    ).join('');
    el('detail-events').innerHTML = events || '<li class="muted">Tiada event.</li>';
}

async function saveDetail(ev) {
    ev.preventDefault();
    const form = ev.currentTarget;
    const msg = el('detail-msg');
    const body = {
        name: form.elements.namedItem('name').value,
        department: form.elements.namedItem('department').value || null,
    };

    msg.textContent = 'Menyimpan...';
    try {
        const res = await fetch(`/office/agents/${selectedId}`, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-CSRF-TOKEN': CONFIG.csrf },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            msg.textContent = res.status === 403 ? 'Hanya owner boleh ubah.' : 'Gagal simpan.';
            return;
        }
        const data = await res.json();
        applyBroadcast(data.agent, null);
        msg.textContent = 'Disimpan.';
    } catch {
        msg.textContent = 'Gagal simpan.';
    }
}
