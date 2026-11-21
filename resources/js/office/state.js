// Store kecil untuk office. Semua UI (Phaser, team, feed) baca dari sini.

const MAX_EVENTS = 200;

const state = {
    agents: new Map(),
    ended: new Map(), // sesi yang baru tamat (24 jam): kekal dalam senarai supaya maklumat tak hilang
    events: [],
    loaded: false, // true selepas snapshot sebenar pertama dari /office/state
};

const listeners = new Set();

function snapshot() {
    return {
        agents: [...state.agents.values()],
        ended: [...state.ended.values()],
        events: state.events,
        loaded: state.loaded,
    };
}

function emit() {
    const snap = snapshot();
    listeners.forEach((fn) => fn(snap));
}

export function subscribe(fn) {
    listeners.add(fn);
    fn(snapshot());

    return () => listeners.delete(fn);
}

// Ganti semua data dengan snapshot dari /office/state (reload, polling).
// Agent yang tak ada dalam snapshot (dah ended) akan dianggap keluar oleh scene.
export function setSnapshot({ agents = [], events = [], ended = [] } = {}) {
    state.agents = new Map(agents.map((a) => [a.id, a]));
    state.ended = new Map(ended.map((a) => [a.id, a]));
    state.events = events.slice(0, MAX_EVENTS);
    state.loaded = true;
    emit();
}

// Event dari broadcast Reverb
export function applyBroadcast(agent, event) {
    state.agents.set(agent.id, agent);

    if (event && !state.events.some((e) => e.id === event.id)) {
        state.events.unshift(event);
        state.events.length = Math.min(state.events.length, MAX_EVENTS);
    }

    emit();
}

export function getAgent(id) {
    return state.agents.get(id) ?? state.ended.get(id) ?? null;
}

export function getEventsFor(agentId, limit = 10) {
    return state.events.filter((e) => e.agent_id === agentId).slice(0, limit);
}
