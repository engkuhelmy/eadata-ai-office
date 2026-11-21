// Mod TV (?tv=1): sembunyi kursor bila tak bergerak.
export const isTv = new URLSearchParams(window.location.search).get('tv') === '1';

export function initTv() {
    if (!isTv) return;
    document.documentElement.classList.add('tv');

    let timer = null;
    const wake = () => {
        document.documentElement.classList.remove('tv-idle');
        clearTimeout(timer);
        timer = setTimeout(() => document.documentElement.classList.add('tv-idle'), 2000);
    };
    document.addEventListener('mousemove', wake);
    wake();
}
