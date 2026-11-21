import '../bootstrap';
import Phaser from 'phaser';
import OfficeScene from './OfficeScene';
import * as store from './state';
import * as ui from './ui';
import { connectRealtime } from './realtime';
import { initPanels } from './panels';
import { initNotify, checkTransitions } from './notify';
import { initTv, isTv } from './tv';

initTv();
ui.initFilters();
initNotify({ openAgent: (id) => ui.showDetail(id) });
if (!isTv) initPanels({ onOpenAgent: (id) => ui.showDetail(id) });

const scene = new OfficeScene();
scene.onSelect = (id) => ui.showDetail(id);

window.__officeGame = new Phaser.Game({
    type: Phaser.AUTO,
    parent: 'office-canvas',
    width: 1280,
    height: 720,
    backgroundColor: '#2a2219',
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: [scene],
});

store.subscribe((snap) => {
    ui.renderTeam(snap.agents, snap.ended);
    ui.renderFeed(snap.events);
    ui.refreshDetail();
    checkTransitions(snap.agents, snap.loaded);
    scene.render(snap.agents);
});

connectRealtime({
    onSnapshot: (data) => store.setSnapshot(data),
    onAgent: (agent, event) => store.applyBroadcast(agent, event),
    onStatus: (status) => ui.setStatus(status),
});
