// Halaman /history: tapis dan senarai event lama, dengan "Muat lebih".
import { DEPARTMENTS, VENDOR_COLORS } from './layout';
import { esc, hex, getJson } from './util';

const $ = (id) => document.getElementById(id);

let page = 1;
let loading = false;

function today() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function row(e) {
    const time = e.ts ? new Date(e.ts).toLocaleTimeString('en-GB', { hour12: false }) : '';
    const color = hex(VENDOR_COLORS[e.vendor] ?? 0x64748b);
    return `<tr>
        <td class="time">${esc(time)}</td>
        <td>${esc(e.agent)}</td>
        <td><span class="dot" style="background:${color}"></span>${esc(e.vendor)}</td>
        <td>${esc(e.event)}</td>
        <td>${esc(e.tool ?? '')}</td>
        <td class="target">${esc(e.target ?? '')}</td>
        <td>${esc(DEPARTMENTS[e.department]?.label ?? e.department ?? '')}</td>
    </tr>`;
}

async function load(reset) {
    if (loading) return;
    loading = true;
    if (reset) page = 1;

    const msg = $('h-msg');
    const more = $('h-more');
    const body = $('h-body');
    msg.textContent = 'Memuatkan...';
    more.hidden = true;

    const q = new URLSearchParams({ page: String(page) });
    [['date', 'f-date'], ['vendor', 'f-vendor'], ['project', 'f-project'], ['pc', 'f-pc'], ['agent_id', 'f-agent']]
        .forEach(([key, id]) => {
            const v = $(id).value.trim();
            if (v) q.set(key, v);
        });

    try {
        const res = await getJson(`/office/history.json?${q}`);
        const rows = Array.isArray(res.data) ? res.data : [];
        if (reset) body.innerHTML = '';
        body.insertAdjacentHTML('beforeend', rows.map(row).join(''));
        msg.textContent = body.children.length ? '' : 'Tiada event untuk penapis ini.';
        more.hidden = !res.has_more;
    } catch {
        msg.textContent = 'Sejarah tidak tersedia.';
    } finally {
        loading = false;
    }
}

// Isi pilihan agent / PC / projek dari keadaan semasa (tak kritikal kalau gagal)
async function loadOptions() {
    try {
        const state = await getJson('/office/state');
        const agents = state.agents ?? [];
        $('f-agent').insertAdjacentHTML('beforeend', agents
            .map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join(''));
        const uniq = (k) => [...new Set(agents.map((a) => a[k]).filter(Boolean))].sort();
        $('dl-pc').innerHTML = uniq('pc').map((v) => `<option value="${esc(v)}">`).join('');
        $('dl-project').innerHTML = uniq('project').map((v) => `<option value="${esc(v)}">`).join('');
    } catch {
        // abaikan
    }
}

document.addEventListener('DOMContentLoaded', () => {
    $('f-date').value = today();
    $('h-filters').addEventListener('submit', (ev) => {
        ev.preventDefault();
        load(true);
    });
    $('h-more').addEventListener('click', () => {
        page += 1;
        load(false);
    });
    loadOptions();
    load(true);
});
