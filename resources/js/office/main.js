import '../bootstrap';
import Phaser from 'phaser';
import OfficeScene from './OfficeScene';
import { CANVAS, FLOORS } from './layout';
import * as store from './state';
import * as ui from './ui';
import { connectRealtime } from './realtime';
import { initPanels } from './panels';
import { initNotify, checkTransitions, checkDone, sfx } from './notify';
import { initAttention, updateAttention } from './attention';
import { initTv, isTv } from './tv';
import { lsGet, lsSet } from './util';

const VIEW_KEY = 'office.view';
const TV_CYCLE_MS = 15000;

const scene = new OfficeScene();
let counts = ui.countByFloor([]);

// Pilih staff: buka butiran dan zoom ke aras staff itu
const openAgent = (id) => {
    ui.showDetail(id);
    scene.focusAgent(id);
};

let tvTimer = null;
const setView = (view) => {
    scene.setView(view);
    if (!isTv) lsSet(VIEW_KEY, String(view));
    if (isTv && !window.OFFICE.embed) restartTvCycle();
};

initTv();
ui.initFilters();
ui.setOnFocus((id) => scene.focusAgent(id));
ui.initFloorTabs({ onView: setView });
initNotify({ openAgent });
if (!isTv) {
    initPanels({ onOpenAgent: openAgent });
    initAttention({
        openAgent,
        setView,
        deselect: () => { scene.selectedId = null; },
    });
}

// Pentas pelancaran: staff yang siap pusingan kerja >= 2 minit membentang di auditorium (L1)
const LAUNCH_MIN_SECONDS = 120;
scene.onLaunch = () => sfx('launch');

scene.onSelect = (id) => ui.showDetail(id);
scene.onViewChange = (view) => ui.setActiveView(view);

// Paparan awal: bangunan (TV), atau paparan terakhir pengguna
const saved = isTv ? 'building' : lsGet(VIEW_KEY, 'building');
scene.setView(saved === 'building' ? 'building' : Number(saved));
ui.setActiveView(scene.view);

window.__officeGame = new Phaser.Game({
    type: Phaser.AUTO,
    parent: 'office-canvas',
    width: CANVAS.w,
    height: CANVAS.h,
    backgroundColor: '#2a2219',
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: [scene],
});

// Saiz bekas berubah (putar telefon, sidebar, tab dipapar semula): muat semula skala canvas
const refreshScale = () => window.__officeGame.scale.refresh();
if ('ResizeObserver' in window) {
    new ResizeObserver(refreshScale).observe(document.getElementById('office-canvas'));
}
window.addEventListener('resize', refreshScale);
window.addEventListener('orientationchange', refreshScale);

store.subscribe((snap) => {
    counts = ui.countByFloor(snap.agents);
    ui.renderTeam(snap.agents, snap.ended);
    ui.renderFeed(snap.events);
    ui.refreshDetail();
    ui.updateFloorTabs(counts);
    checkTransitions(snap.agents, snap.loaded);
    const fresh = isTv ? [] : checkDone(snap.agents, snap.loaded);
    if (!isTv) updateAttention(snap.agents);
    scene.setFloorCounts(counts);
    scene.render(snap.agents, { loaded: snap.loaded });
    for (const a of fresh) {
        if ((a.last_turn_seconds ?? 0) >= LAUNCH_MIN_SECONDS) scene.present(a.id, a.name);
    }
});

// Mod TV: pusing Bangunan -> L1 -> L2 -> L3 -> Rooftop (~15s setiap satu), langkau aras kosong
function restartTvCycle() {
    clearInterval(tvTimer);
    const order = ['building', ...FLOORS.map((f) => f.id)];
    tvTimer = setInterval(() => {
        const at = Math.max(0, order.indexOf(scene.view));
        for (let k = 1; k <= order.length; k++) {
            const v = order[(at + k) % order.length];
            if (v === 'building' || (counts[v] ?? 0) > 0) {
                scene.setView(v);
                break;
            }
        }
    }, TV_CYCLE_MS);
}
if (isTv && !window.OFFICE.embed) restartTvCycle();

connectRealtime({
    onSnapshot: (data) => store.setSnapshot(data),
    onAgent: (agent, event) => store.applyBroadcast(agent, event),
    onStatus: (status) => ui.setStatus(status),
});
