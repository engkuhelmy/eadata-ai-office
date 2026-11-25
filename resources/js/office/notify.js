// Notifikasi operator: banner + beep bila agent masuk status yang perlukan perhatian.
import { esc, lsGet, lsSet } from './util';

const ALERT_MSG = {
    needs_approval: 'perlu approval',
    error: 'ada error',
    rate_limited: 'kena rate limit',
};

const SOUND_KEY = 'office.sound';
const MAX_BANNERS = 4;

let prev = null; // Map id -> status; null sehingga snapshot pertama dimuatkan
let onOpen = () => {};
let ctx = null;
let soundOn = lsGet(SOUND_KEY, 'on') !== 'off';

function ensureCtx() {
    try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        ctx ??= new AC();
        if (ctx.state === 'suspended') ctx.resume();
    } catch {
        ctx = null;
    }
    return ctx;
}

function beep() {
    if (!soundOn || !ctx || ctx.state !== 'running') return;
    try {
        const now = ctx.currentTime;
        [880, 660].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.0001, now + i * 0.18);
            gain.gain.exponentialRampToValueAtTime(0.15, now + i * 0.18 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.18 + 0.16);
            osc.connect(gain).connect(ctx.destination);
            osc.start(now + i * 0.18);
            osc.stop(now + i * 0.18 + 0.18);
        });
    } catch {
        // audio gagal, abaikan
    }
}

// Urutan nada pendek: [frekuensi, mula (s), tempoh (s)]
function tones(notes, volume = 0.12, type = 'sine') {
    if (!soundOn || !ctx || ctx.state !== 'running') return;
    try {
        const now = ctx.currentTime;
        for (const [freq, at, dur] of notes) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = type;
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.0001, now + at);
            gain.gain.exponentialRampToValueAtTime(volume, now + at + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + at + dur);
            osc.connect(gain).connect(ctx.destination);
            osc.start(now + at);
            osc.stop(now + at + dur + 0.02);
        }
    } catch {
        // audio gagal, abaikan
    }
}

// Bunyi UI: 'done' (chime lembut, staff siap), 'launch' (fanfare pentas)
export function sfx(name) {
    if (name === 'done') tones([[784, 0, 0.25], [1047, 0.12, 0.4]], 0.07);
    if (name === 'launch') tones([[523, 0, 0.18], [659, 0.15, 0.18], [784, 0.3, 0.18], [1047, 0.45, 0.6]], 0.09, 'triangle');
}

function barNode() {
    let bar = document.getElementById('alert-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'alert-bar';
        document.body.appendChild(bar);
    }
    return bar;
}

function showBanner(agent, status, msg = ALERT_MSG[status]) {
    const bar = barNode();
    const item = document.createElement('div');
    item.className = `alert-item ${status}`;
    item.innerHTML = `<button type="button" class="alert-open">${esc(agent.name)} ${esc(msg)}</button>
        <button type="button" class="alert-close" aria-label="Tutup">&times;</button>`;
    item.querySelector('.alert-open').addEventListener('click', () => {
        onOpen(agent.id);
        item.remove();
    });
    item.querySelector('.alert-close').addEventListener('click', () => item.remove());
    bar.appendChild(item);
    while (bar.children.length > MAX_BANNERS) bar.firstElementChild.remove();
    // Banner "siap" hilang sendiri (bukan kecemasan); alert lain kekal sampai ditutup
    if (status === 'done') setTimeout(() => item.remove(), 8000);
}

// "12 min" / "45 saat" untuk tempoh pusingan kerja
export function fmtDuration(sec) {
    const s = Math.max(0, Math.round(Number(sec) || 0));
    if (s < 60) return `${s} saat`;
    const m = Math.round(s / 60);
    return m < 60 ? `${m} min` : `${Math.floor(m / 60)} jam ${m % 60} min`;
}

// Toast untuk staff yang baru siap (sekali bagi setiap done_at baru). Staff demo diabaikan.
let prevDone = null;
export function checkDone(agents, loaded) {
    if (!loaded) return [];
    const next = new Map(agents.map((a) => [a.id, a.done_at ?? null]));
    if (prevDone === null) {
        prevDone = next;
        return [];
    }
    const fresh = agents.filter((a) => a.pc !== 'DEMO-PC' && a.status === 'idle' && a.done_at && prevDone.get(a.id) !== a.done_at);
    prevDone = next;
    for (const a of fresh) {
        showBanner(a, 'done', a.last_turn_seconds ? `siap (${fmtDuration(a.last_turn_seconds)}), tunggu arahan` : 'siap, tunggu arahan');
    }
    if (fresh.length) sfx('done');
    return fresh;
}

// Dipanggil pada setiap perubahan snapshot. `loaded` = snapshot sebenar dah diterima.
export function checkTransitions(agents, loaded) {
    if (!loaded) return;

    const next = new Map(agents.map((a) => [a.id, a.status]));
    if (prev === null) {
        prev = next;
        return;
    }

    let alerted = false;
    for (const a of agents) {
        // Staff demo (pc DEMO-PC) sengaja minta approval/error: loceng dalam office sahaja, tiada banner atau bunyi
        if (a.pc === 'DEMO-PC') continue;
        if (ALERT_MSG[a.status] && prev.get(a.id) !== a.status) {
            showBanner(a, a.status);
            alerted = true;
        }
    }
    prev = next;
    if (alerted) beep();
}

function paintToggle() {
    const btn = document.getElementById('sound-toggle');
    if (btn) btn.textContent = `Bunyi: ${soundOn ? 'on' : 'off'}`;
}

export function initNotify({ openAgent } = {}) {
    if (openAgent) onOpen = openAgent;

    // AudioContext hanya dicipta selepas klik pertama (polisi autoplay)
    document.addEventListener('click', ensureCtx, { once: true });

    const btn = document.getElementById('sound-toggle');
    paintToggle();
    btn?.addEventListener('click', () => {
        soundOn = !soundOn;
        lsSet(SOUND_KEY, soundOn ? 'on' : 'off');
        paintToggle();
        if (soundOn) {
            ensureCtx();
            beep();
        }
    });
}
