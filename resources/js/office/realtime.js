// Sambungan live: Reverb (private channel `office`) + fallback polling /office/state.

const POLL_MS = 3000;
const SYNC_EVERY_TICKS_WHEN_LIVE = 10; // ~30s sync walaupun WS sihat

export function connectRealtime({ onSnapshot, onAgent, onStatus }) {
    let live = false;
    let ticks = 0;

    async function sync() {
        try {
            const res = await fetch('/office/state', {
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
            });
            if (res.ok) {
                onSnapshot(await res.json());
            }
        } catch {
            // rangkaian putus, cuba lagi tick seterusnya
        }
    }

    try {
        window.Echo.private('office').listen('.agent.updated', ({ agent, event }) => {
            onAgent(agent, event ?? null);
        });

        window.Echo.connector?.pusher?.connection?.bind('state_change', ({ current }) => {
            live = current === 'connected';
            onStatus(live ? 'live' : 'polling');
        });
    } catch (err) {
        console.warn('Echo tak dapat disambung, guna polling sahaja.', err);
    }

    sync();
    setInterval(() => {
        ticks++;
        if (!live || ticks % SYNC_EVERY_TICKS_WHEN_LIVE === 0) {
            sync();
        }
    }, POLL_MS);

    onStatus('polling');
}
