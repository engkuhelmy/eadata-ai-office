// Helper kecil yang dikongsi oleh modul UI office dan halaman sejarah.

export const esc = (value) =>
    String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[ch]);

export const hex = (n) => `#${Number(n).toString(16).padStart(6, '0')}`;

export const fmtNum = (n) => Number(n || 0).toLocaleString('en-US');

export function lsGet(key, fallback = null) {
    try {
        const v = window.localStorage.getItem(key);
        return v === null ? fallback : v;
    } catch {
        return fallback;
    }
}

export function lsSet(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch {
        // storan disekat, abaikan
    }
}

// "2 min lalu" dari ISO timestamp
export function relTime(iso) {
    if (!iso) return 'tiada';
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return 'tiada';
    const s = Math.max(0, Math.round((Date.now() - t) / 1000));
    if (s < 60) return `${s} saat lalu`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m} min lalu`;
    const h = Math.floor(m / 60);
    if (h < 48) return `${h} jam lalu`;
    return `${Math.floor(h / 24)} hari lalu`;
}

export async function getJson(url) {
    const res = await fetch(url, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}
