// Perhatian operator (diambil dari Agent Office Kit): pil ringkas "n approval · n error · n siap" yang buka senarai,
// kunci pintas papan kekunci (Tab = staff seterusnya ikut keutamaan, Esc, 0-4 = aras).
import { esc, relTime } from './util';
import { fmtDuration } from './notify';

// Keutamaan: approval > error > siap (tunggu arahan) > rate limit > kerja > standby
const RANK = { needs_approval: 0, error: 1, done: 2, rate_limited: 3, active: 4, idle: 5 };

const isDone = (a) => a.status === 'idle' && !!a.done_at;
const rankOf = (a) => (isDone(a) ? RANK.done : RANK[a.status] ?? 9);

let agents = [];
let cursor = null; // id staff terakhir yang dipilih melalui Tab
let open = false;
let onOpen = () => {};

const el = (id) => document.getElementById(id);

// Staff di peta (bukan Off / tamat), disusun ikut keutamaan kemudian nama
function ranked() {
    return agents
        .filter((a) => a.status !== 'off' && a.status !== 'ended')
        .sort((x, y) => rankOf(x) - rankOf(y) || String(x.name).localeCompare(String(y.name)));
}

function attentionList() {
    return ranked().filter((a) => rankOf(a) <= RANK.done);
}

function render() {
    const pill = el('attn-pill');
    if (!pill) return;

    const list = attentionList();
    const n = (k) => list.filter((a) => rankOf(a) === RANK[k]).length;
    const parts = [
        n('needs_approval') ? `<span class="a-appr">\u{1F510} ${n('needs_approval')} approval</span>` : '',
        n('error') ? `<span class="a-err">⚠ ${n('error')} error</span>` : '',
        n('done') ? `<span class="a-done">✅ ${n('done')} siap</span>` : '',
    ].filter(Boolean);

    pill.innerHTML = parts.length ? parts.join(' · ') : '<span class="muted">Semua OK</span>';
    pill.classList.toggle('hot', n('needs_approval') + n('error') > 0);
    pill.setAttribute('aria-expanded', open ? 'true' : 'false');

    const menu = el('attn-menu');
    if (!menu) return;
    menu.hidden = !open;
    if (!open) return;
    menu.innerHTML = list.length
        ? list.map((a) => {
            const why = a.status === 'needs_approval' ? (a.current_task || 'Perlu approval')
                : a.status === 'error' ? 'Ada error'
                    : `Siap ${relTime(a.done_at)}${a.last_turn_seconds ? ` · kerja ${fmtDuration(a.last_turn_seconds)}` : ''}`;
            return `<button type="button" data-id="${a.id}" class="attn-row r${rankOf(a)}"><b>${esc(a.name)}</b><span>${esc(why)}</span></button>`;
        }).join('')
        : '<p class="muted small">Tiada staff perlukan perhatian.</p>';
    menu.querySelectorAll('[data-id]').forEach((b) => b.addEventListener('click', () => {
        setOpen(false);
        onOpen(Number(b.dataset.id));
    }));
}

function setOpen(v) {
    open = v;
    render();
}

export function updateAttention(list) {
    agents = list;
    render();
}

// Tab / Shift+Tab: lompat ke staff seterusnya ikut keutamaan
function cycle(dir) {
    const list = ranked();
    if (!list.length) return;
    const at = list.findIndex((a) => a.id === cursor);
    const next = list[(at + dir + list.length) % list.length] ?? list[0];
    cursor = next.id;
    onOpen(next.id);
}

const typing = (t) => t && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName));

export function initAttention({ openAgent, setView, deselect }) {
    onOpen = openAgent;
    el('attn-pill')?.addEventListener('click', (ev) => {
        ev.stopPropagation();
        setOpen(!open);
    });
    document.addEventListener('click', (ev) => {
        if (open && !ev.target.closest?.('#attn-menu')) setOpen(false);
    });

    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') {
            if (open) setOpen(false);
            else deselect?.();
            if (typing(ev.target)) ev.target.blur();
            return;
        }
        if (typing(ev.target) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
        if (ev.key === 'Tab') {
            ev.preventDefault();
            cycle(ev.shiftKey ? -1 : 1);
        } else if (ev.key === '0') {
            setView('building');
        } else if (/^[1-4]$/.test(ev.key)) {
            setView(Number(ev.key));
        }
    });
    render();
}
