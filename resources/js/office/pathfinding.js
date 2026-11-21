// A* ringkas pada grid 4-arah. blocked = Set berbentuk "c,r".
// Return: array tile (tanpa start, termasuk goal). [] kalau dah di goal. null kalau tiada laluan.

export function findPath(start, goal, blocked, cols, rows) {
    if (start.c === goal.c && start.r === goal.r) {
        return [];
    }

    const key = (c, r) => `${c},${r}`;
    const h = (c, r) => Math.abs(c - goal.c) + Math.abs(r - goal.r);
    const open = [{ c: start.c, r: start.r, g: 0, f: h(start.c, start.r), parent: null }];
    const bestG = new Map([[key(start.c, start.r), 0]]);
    const closed = new Set();
    const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];

    while (open.length) {
        let bi = 0;
        for (let i = 1; i < open.length; i++) {
            if (open[i].f < open[bi].f) bi = i;
        }
        const cur = open.splice(bi, 1)[0];
        const ck = key(cur.c, cur.r);

        if (cur.c === goal.c && cur.r === goal.r) {
            const path = [];
            for (let n = cur; n.parent; n = n.parent) {
                path.unshift({ c: n.c, r: n.r });
            }
            return path;
        }

        if (closed.has(ck)) continue;
        closed.add(ck);

        for (const [dc, dr] of dirs) {
            const nc = cur.c + dc;
            const nr = cur.r + dr;
            if (nc < 0 || nr < 0 || nc >= cols || nr >= rows) continue;

            const nk = key(nc, nr);
            const isGoal = nc === goal.c && nr === goal.r;
            if (!isGoal && blocked.has(nk)) continue;
            if (closed.has(nk)) continue;

            const g = cur.g + 1;
            if (g < (bestG.get(nk) ?? Infinity)) {
                bestG.set(nk, g);
                open.push({ c: nc, r: nr, g, f: g + h(nc, nr), parent: cur });
            }
        }
    }

    return null;
}
