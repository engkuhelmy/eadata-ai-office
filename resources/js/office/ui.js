import { AVATARS, AVATAR_LABELS, DEPARTMENTS, FLOORS, VENDOR_COLORS, floorOf } from './layout';
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
    off: 'Off',
};

const STATUS_COLOR = {
    active: '#10a37f',
    idle: '#a89c8c',
    error: '#e53935',
    needs_approval: '#f5b841',
    rate_limited: '#64748b',
    ended: '#6b6257',
    off: '#9a8f80',
};

let selectedId = null;
let onFocus = () => {};

// Dipanggil bila staff dipilih dari senarai Team: scene zoom ke aras staff itu
export function setOnFocus(fn) {
    onFocus = fn;
}

// Tag pendek aras: 'L1', 'L2', 'L3', 'Rooftop'
export function floorTag(id) {
    const f = FLOORS.find((x) => x.id === id);
    if (!f) return '';
    return /^level/i.test(f.label ?? '') ? f.key : f.label;
}

// Kiraan staff setiap aras (ikut department sasaran). { building: jumlah, [floorId]: n }
export function countByFloor(agents) {
    const counts = { building: 0 };
    for (const f of FLOORS) counts[f.id] = 0;
    for (const a of agents) {
        if (a.status === 'ended' || a.status === 'off') continue;
        const f = floorOf(a.department ?? 'door');
        counts[f] = (counts[f] ?? 0) + 1;
        counts.building++;
    }
    return counts;
}

// Tab aras di atas canvas: Bangunan | L1 | L2 | L3 | Rooftop, setiap satu dengan kiraan staff
let activeView = 'building';

export function initFloorTabs({ onView }) {
    const nav = el('floor-tabs');
    if (nav) {
        const tabs = [{ view: 'building', label: 'Bangunan' }, ...FLOORS.map((f) => ({ view: String(f.id), label: floorTag(f.id), title: `${f.label} · ${f.name}` }))];
        nav.innerHTML = tabs.map((t) => `<button type="button" data-view="${esc(t.view)}"${t.title ? ` title="${esc(t.title)}"` : ''}>${esc(t.label)} <span class="n">0</span></button>`).join('');
        nav.querySelectorAll('button').forEach((b) => {
            b.addEventListener('click', () => onView(b.dataset.view === 'building' ? 'building' : Number(b.dataset.view)));
        });
    }
    el('back-building')?.addEventListener('click', () => onView('building'));
    setActiveView(activeView);
}

export function setActiveView(view) {
    activeView = view;
    el('floor-tabs')?.querySelectorAll('button').forEach((b) => {
        const on = b.dataset.view === String(view);
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    const back = el('back-building');
    if (back) back.hidden = view === 'building';
}

export function updateFloorTabs(counts) {
    el('floor-tabs')?.querySelectorAll('button').forEach((b) => {
        const n = b.querySelector('.n');
        if (n) n.textContent = String(counts[b.dataset.view] ?? 0);
    });
}

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

// 'L2 · IT · Backend'
function teamPlace(key) {
    const dept = DEPARTMENTS[key];
    if (!dept) return '';
    const tag = floorTag(floorOf(key));
    return tag ? `${tag} · ${dept.label}` : dept.label;
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
        // Staf Off di bawah sekali
        const list = [...groups[project]].sort((x, y) => (x.status === 'off') - (y.status === 'off'));
        const rows = list.map((a) => {
            const off = a.status === 'off';
            const meta = a.staff?.role ?? a.label;
            const task = off
                ? (a.last_event_at ? `Habis kerja ${relTime(a.last_event_at)}` : 'Belum check in') + (a.staff?.home ? ` · meja ${teamPlace(a.staff.home)}` : '')
                : teamPlace(a.department) + (a.current_task ? ' · ' + a.current_task : '');
            return `
            <li data-id="${a.id}" class="row${off ? ' off-row' : ''}">
                <span class="dot" style="background:${hex(VENDOR_COLORS[a.vendor] ?? 0x64748b)}${off ? ';opacity:.4' : ''}"></span>
                <span class="name">${esc(a.name)}${a.staff ? ' <span class="staff-tag" title="Staf sebenar (Staff OS)">Staf</span>' : ''}</span>
                <span class="meta">${esc(meta)}</span>
                <span class="status" style="color:${STATUS_COLOR[a.status] ?? '#a89c8c'}">${esc(STATUS_LABEL[a.status] ?? a.status)}</span>
                <span class="task">${esc(task)}</span>
            </li>`;
        }).join('');

        return `<h3>${esc(project)} <span class="count">${groups[project].length}</span></h3><ul>${rows}</ul>`;
    }).join('');

    const empty = agents.length
        ? '<p class="muted">Tiada agent padan dengan penapis.</p>'
        : '<p class="muted">Tiada agent lagi. Jalankan <code>php artisan office:simulate</code>.</p>';
    node.innerHTML = (html || (lastEnded.length ? '<p class="muted">Tiada agent aktif sekarang.</p>' : empty)) + endedSection();
    node.querySelectorAll('.row').forEach((row) => {
        row.addEventListener('click', () => {
            const id = Number(row.dataset.id);
            showDetail(id);
            if (!row.classList.contains('ended-row') && !row.classList.contains('off-row')) onFocus(id);
        });
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

    // Department dikumpul ikut aras (optgroup)
    const option = (k) => `<option value="${esc(k)}" ${a.pinned_department === k ? 'selected' : ''}>${esc(deptLabel(k))}</option>`;
    const options = FLOORS.map((f) => {
        const keys = CONFIG.departments.filter((k) => floorOf(k) === f.id);
        if (!keys.length) return '';
        return `<optgroup label="${esc(`${f.label} · ${f.name}`)}">${keys.map(option).join('')}</optgroup>`;
    }).join('') + CONFIG.departments.filter((k) => !FLOORS.some((f) => f.id === floorOf(k))).map(option).join('');

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

// Profil Staff OS: jawatan, lapor kepada, meja tetap, skop dan handoff
function staffRows(st) {
    if (!st) return '';
    const list = (items, max) => items.length
        ? `<ul class="staff-list">${items.slice(0, max).map((x) => `<li>${esc(x)}</li>`).join('')}${items.length > max ? `<li class="muted">+${items.length - max} lagi</li>` : ''}</ul>`
        : '-';
    return `
        <dt>Jawatan</dt><dd>${esc(st.role ?? '-')}</dd>
        <dt>Unit</dt><dd>${esc(st.unit ?? '-')}${st.fasa ? ` · Fasa ${esc(st.fasa)}` : ''}</dd>
        <dt>Lapor kepada</dt><dd>${esc(st.reports_to ?? '-')}</dd>
        ${st.team?.length ? `<dt>Team</dt><dd>${esc(st.team.join(', '))}</dd>` : ''}
        <dt>Meja tetap</dt><dd>${esc(st.home ? teamPlace(st.home) : (st.room ?? '-'))}</dd>
        <dt>Brief</dt><dd>${st.checked_in_at ? `Diterima semasa check in ${esc(relTime(st.checked_in_at))}` : '<span class="muted">Belum check in</span>'}${st.active ? '' : ' · <strong>Tidak aktif</strong>'}</dd>
        <dt>Skop</dt><dd>${list(st.scope ?? [], 6)}</dd>
        <dt>Handoff</dt><dd>${list(st.handoffs ?? [], 6)}</dd>`;
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
        <dt>Department</dt><dd>${a.department && DEPARTMENTS[a.department] ? esc(floorTag(floorOf(a.department))) + ' · ' : ''}${esc(deptLabel(a.department))}${a.pinned_department ? ' <span class="pin">dipin</span>' : ''}</dd>
        <dt>Status</dt><dd>${esc(STATUS_LABEL[a.status] ?? a.status)}</dd>
        <dt>Task</dt><dd>${esc(a.current_task ?? '-')}</dd>${tokenRow(a.usage)}${staffRows(a.staff)}`;

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
