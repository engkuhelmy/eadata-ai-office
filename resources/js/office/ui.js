import { AVATARS, AVATAR_LABELS, DEPARTMENTS, VENDOR_COLORS } from './layout';
import { applyBroadcast, getAgent, getEventsFor } from './state';
import { esc, hex, fmtNum, lsGet, lsSet, relTime } from './util';

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

const el = (id) => document.getElementById(id);

// Penapis Team (PC, Projek): disimpan dalam localStorage
const FILTER_KEYS = { pc: 'office.filter.pc', project: 'office.filter.project' };
const filters = { pc: lsGet(FILTER_KEYS.pc, ''), project: lsGet(FILTER_KEYS.project, '') };
let lastAgents = [];
let filterSig = '';

function fillSelect(select, values, current, allLabel) {
    select.innerHTML = `<option value="">${esc(allLabel)}</option>` +
        values.map((v) => `<option value="${esc(v)}" ${v === current ? 'selected' : ''}>${esc(v)}</option>`).join('');
}

function syncFilterOptions(agents) {
    const pcSel = el('flt-pc');
    const prSel = el('flt-project');
    if (!pcSel || !prSel || !agents.length) return;

    const pcs = [...new Set(agents.map((a) => a.pc).filter(Boolean))].sort();
    const projects = [...new Set(agents.map((a) => a.project).filter(Boolean))].sort();
    if (filters.pc && !pcs.includes(filters.pc)) filters.pc = '';
    if (filters.project && !projects.includes(filters.project)) filters.project = '';

    const sig = JSON.stringify([pcs, projects, filters.pc, filters.project]);
    if (sig === filterSig) return;
    filterSig = sig;
    fillSelect(pcSel, pcs, filters.pc, 'Semua PC');
    fillSelect(prSel, projects, filters.project, 'Semua projek');
}

export function initFilters() {
    [['flt-pc', 'pc'], ['flt-project', 'project']].forEach(([id, key]) => {
        el(id)?.addEventListener('change', (e) => {
            filters[key] = e.target.value;
            lsSet(FILTER_KEYS[key], filters[key]);
            renderTeam(lastAgents);
        });
    });
}

export function setStatus(status) {
    const node = el('live-status');
    if (!node) return;
    node.textContent = status === 'live' ? 'Live (WebSocket)' : 'Polling 3s';
    node.className = status === 'live' ? 'pill live' : 'pill polling';
}

let lastEnded = [];
let endedOpen = false;

// Senarai sesi yang tamat dalam 24 jam, supaya maklumat agent tak hilang bila sweep tamatkan sesi senyap.
function endedSection() {
    const list = lastEnded.filter((a) => (!filters.pc || a.pc === filters.pc) && (!filters.project || a.project === filters.project));
    if (!list.length) return '';

    const rows = list.map((a) => `
        <li data-id="${a.id}" class="row ended-row">
            <span class="dot" style="background:${hex(VENDOR_COLORS[a.vendor] ?? 0x64748b)}"></span>
            <span class="name">${esc(a.name)}</span>
            <span class="status muted">${esc(relTime(a.ended_at ?? a.last_event_at))}</span>
            <span class="task">${esc(a.label ?? '')}${a.project ? ' · ' + esc(a.project) : ''}</span>
        </li>`).join('');

    return `<details class="ended" ${endedOpen ? 'open' : ''}><summary>Tamat 24 jam <span class="count">${list.length}</span></summary><ul>${rows}</ul></details>`;
}

export function renderTeam(agents, ended = lastEnded) {
    const node = el('team');
    if (!node) return;

    lastAgents = agents;
    lastEnded = ended ?? [];
    syncFilterOptions(agents);

    const groups = {};
    for (const a of agents) {
        if (filters.pc && a.pc !== filters.pc) continue;
        if (filters.project && a.project !== filters.project) continue;
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

    const empty = agents.length
        ? '<p class="muted">Tiada agent padan dengan penapis.</p>'
        : '<p class="muted">Tiada agent lagi. Jalankan <code>php artisan office:simulate</code>.</p>';
    node.innerHTML = (html || (lastEnded.length ? '<p class="muted">Tiada agent aktif sekarang.</p>' : empty)) + endedSection();
    node.querySelectorAll('.row').forEach((row) => {
        row.addEventListener('click', () => showDetail(Number(row.dataset.id)));
    });
    node.querySelector('details.ended')?.addEventListener('toggle', (ev) => {
        endedOpen = ev.currentTarget.open;
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
    el('detail')?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
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

    const avatarOptions = AVATARS
        .map((k) => `<option value="${esc(k)}" ${(a.avatar ?? 'default') === k ? 'selected' : ''}>${esc(AVATAR_LABELS[k] ?? k)}</option>`)
        .join('');

    const form = CONFIG.canEdit ? `
        <form id="detail-form" class="edit">
            <label>Nama paparan
                <input name="name" maxlength="100" placeholder="${esc(a.auto_name ?? '')}" value="${esc(a.custom_name ?? '')}">
            </label>
            <label>Department
                <select name="department"><option value="">Auto (ikut kerja)</option>${options}</select>
            </label>
            <label>Gaya watak
                <select name="avatar">${avatarOptions}</select>
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

function tokenRow(u) {
    if (!u) return '';
    const input = Number(u.input) || 0;
    const output = Number(u.output) || 0;
    const cache = (Number(u.cache_read) || 0) + (Number(u.cache_create) || 0);
    if (!input && !output && !cache) return '';
    return `<dt>Token</dt><dd>Input ${fmtNum(input)} · Output ${fmtNum(output)} · Cache ${fmtNum(cache)}</dd>`;
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
        <dt>Task</dt><dd>${esc(a.current_task ?? '-')}</dd>${tokenRow(a.usage)}`;

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
        avatar: form.elements.namedItem('avatar').value || 'default',
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
