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

function barNode() {
    let bar = document.getElementById('alert-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'alert-bar';
        document.body.appendChild(bar);
    }
    return bar;
}

function showBanner(agent, status) {
    const bar = barNode();
    const item = document.createElement('div');
    item.className = `alert-item ${status}`;
    item.innerHTML = `<button type="button" class="alert-open">${esc(agent.name)} ${esc(ALERT_MSG[status])}</button>
        <button type="button" class="alert-close" aria-label="Tutup">&times;</button>`;
    item.querySelector('.alert-open').addEventListener('click', () => {
        onOpen(agent.id);
        item.remove();
    });
    item.querySelector('.alert-close').addEventListener('click', () => item.remove());
    bar.appendChild(item);
    while (bar.children.length > MAX_BANNERS) bar.firstElementChild.remove();
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
