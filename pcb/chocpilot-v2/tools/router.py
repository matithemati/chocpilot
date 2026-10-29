"""Prosty autorouter siatkowy dla 2 warstw (A*), bez zależności zewnętrznych.

Wejście (JSON z gen_pcb.py): obrys płytki, pady (sieć, kształt, warstwy, otwór), otwory NPTH,
ścieżki wstępne i lista sieci z szerokościami. Wyjście (JSON): odcinki ścieżek i przelotki.

Model: siatka co GRID mm na obu warstwach. Dla każdej komórki pamiętana jest odległość do
najbliższej miedzi (d1, sieć n1) i do najbliższej miedzi innej sieci niż n1 (d2) – z tego
wynika odległość od „obcej” miedzi dla dowolnej sieci. Ścieżka o szerokości w może przejść
przez komórkę, gdy obca miedź jest dalej niż CLEAR + w/2; przelotka – gdy dalej niż
CLEAR + VIA/2 na obu warstwach, nie nachodzi na pad i nie jest za blisko innego otworu.
Sieci wielopinowe łączone są po kolei z najbliższym padem (drzewo rośnie od pierwszego padu).
Nieudane połączenia: sieci przenoszone na początek kolejki i całość trasowana od nowa.
"""
import heapq
import json
import math
import sys
import time
from array import array

GRID = 0.25
CLEAR = 0.2          # odstęp miedź–miedź (= reguła DRC)
EDGE_CLEAR = 0.5     # miedź–krawędź płytki
HOLE_CLEAR = 0.25    # miedź–otwór NPTH
VIA_D = 0.6
VIA_DRILL = 0.3
HOLE2HOLE = 0.3
VIA_COST = 14.0
PAD_KEEP = 0.45     # komórki bliżej cudzego padu niż tyle kosztują więcej
PAD_PENALTY = 1.5
CAP = 1.2            # odległości dalsze niż CAP nie są pamiętane
SQ2 = math.sqrt(2)
INF = 1e9


# ---------------------------------------------------------------- geometria
def dist_rect(px, py, cx, cy, hw, hh):
    dx = abs(px - cx) - hw
    dy = abs(py - cy) - hh
    if dx <= 0 and dy <= 0:
        return 0.0
    return math.hypot(max(dx, 0.0), max(dy, 0.0))


def dist_seg(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L))
    return math.hypot(px - x1 - t * vx, py - y1 - t * vy)


class Shape:
    """Miedź: prostokąt (osiowy), okrąg albo odcinek z promieniem (owal / ścieżka)."""

    def __init__(self, kind, **k):
        self.kind = kind
        self.__dict__.update(k)
        if kind == 'rect':
            self.bb = (self.cx - self.hw, self.cy - self.hh, self.cx + self.hw, self.cy + self.hh)
        elif kind == 'circle':
            self.bb = (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)
        else:
            self.bb = (min(self.x1, self.x2) - self.r, min(self.y1, self.y2) - self.r,
                       max(self.x1, self.x2) + self.r, max(self.y1, self.y2) + self.r)

    def dist(self, px, py):
        if self.kind == 'rect':
            return dist_rect(px, py, self.cx, self.cy, self.hw, self.hh)
        if self.kind == 'circle':
            return max(0.0, math.hypot(px - self.cx, py - self.cy) - self.r)
        return max(0.0, dist_seg(px, py, self.x1, self.y1, self.x2, self.y2) - self.r)


def pad_shape(p):
    x, y = p['x'], p['y']
    w, h = p['w'], p['h']
    rot = round(p.get('rot', 0)) % 180
    if rot == 90:
        w, h = h, w
    if p['shape'] == 'circle':
        return Shape('circle', cx=x, cy=y, r=w / 2)
    if p['shape'] == 'oval':
        if abs(w - h) < 1e-6:
            return Shape('circle', cx=x, cy=y, r=w / 2)
        if w > h:
            return Shape('seg', x1=x - (w - h) / 2, y1=y, x2=x + (w - h) / 2, y2=y, r=h / 2)
        return Shape('seg', x1=x, y1=y - (h - w) / 2, x2=x, y2=y + (h - w) / 2, r=w / 2)
    return Shape('rect', cx=x, cy=y, hw=w / 2, hh=h / 2)


# ---------------------------------------------------------------- siatka
class Grid:
    def __init__(self, W, H):
        self.nx = int(round(W / GRID)) + 1
        self.ny = int(round(H / GRID)) + 1
        self.N = self.nx * self.ny
        n = self.N
        self.d1 = [array('f', [CAP]) * n for _ in range(2)]
        self.n1 = [array('i', [0]) * n for _ in range(2)]
        self.d2 = [array('f', [CAP]) * n for _ in range(2)]
        self.pad_any = [array('f', [CAP]) * n for _ in range(2)]
        self.pad_net = [array('i', [0]) * n for _ in range(2)]
        self.drill = array('f', [CAP]) * n
        self.edge = array('f', [0.0]) * n

    def idx(self, ix, iy):
        return iy * self.nx + ix

    def xy(self, i):
        return (i % self.nx) * GRID, (i // self.nx) * GRID

    def cells_near(self, bb, margin):
        x0 = max(0, int(math.floor((bb[0] - margin) / GRID)))
        y0 = max(0, int(math.floor((bb[1] - margin) / GRID)))
        x1 = min(self.nx - 1, int(math.ceil((bb[2] + margin) / GRID)))
        y1 = min(self.ny - 1, int(math.ceil((bb[3] + margin) / GRID)))
        for iy in range(y0, y1 + 1):
            base = iy * self.nx
            py = iy * GRID
            for ix in range(x0, x1 + 1):
                yield base + ix, ix * GRID, py

    def add_copper(self, shape, layers, net):
        for L in layers:
            d1, n1, d2 = self.d1[L], self.n1[L], self.d2[L]
            for i, px, py in self.cells_near(shape.bb, CAP):
                d = shape.dist(px, py)
                if d >= CAP:
                    continue
                if n1[i] == net:
                    if d < d1[i]:
                        d1[i] = d
                elif d < d1[i]:
                    d2[i] = d1[i]
                    d1[i] = d
                    n1[i] = net
                elif d < d2[i]:
                    d2[i] = d

    def add_pad_any(self, shape, layers, net):
        for L in layers:
            pa, pn = self.pad_any[L], self.pad_net[L]
            for i, px, py in self.cells_near(shape.bb, CAP):
                d = shape.dist(px, py)
                if d < pa[i]:
                    pa[i] = d
                    pn[i] = net

    def add_drill(self, cx, cy, r):
        s = Shape('circle', cx=cx, cy=cy, r=r)
        for i, px, py in self.cells_near(s.bb, CAP):
            d = s.dist(px, py)
            if d < self.drill[i]:
                self.drill[i] = d

    def foreign(self, L, i, net):
        return self.d1[L][i] if self.n1[L][i] != net else self.d2[L][i]


# ---------------------------------------------------------------- router
class Router:
    def __init__(self, data):
        self.data = data
        self.W, self.H = data['board']['w'], data['board']['h']
        self.netid = {}
        for n in data['nets']:
            self.netid[n['name']] = len(self.netid) + 1
        self.width = {n['name']: n['width'] for n in data['nets']}
        self.fallback = {}
        self.plane_nets = set(data.get('plane_nets', []))

    def build_static(self):
        g = Grid(self.W, self.H)
        # odległość od krawędzi (prostokąt z zaokrąglonymi narożnikami)
        R = self.data['board'].get('corner', 0.0)
        for i in range(g.N):
            x, y = g.xy(i)
            d = min(x, y, self.W - x, self.H - y)
            cx = min(max(x, R), self.W - R)
            cy = min(max(y, R), self.H - R)
            if (cx, cy) != (x, y):
                d = min(d, R - math.hypot(x - cx, y - cy))
            g.edge[i] = d
        self.pads = []
        for p in self.data['pads']:
            s = pad_shape(p)
            layers = p['layers']
            net = self.netid.get(p['net'], -1) if p['net'] else -1
            g.add_copper(s, layers, net)
            g.add_pad_any(s, layers, net)
            if p.get('drill'):
                g.add_drill(p['x'], p['y'], p['drill'] / 2)
            self.pads.append((p, s, net))
        for h in self.data['holes']:      # NPTH: przeszkoda na obu warstwach + otwór
            s = Shape('circle', cx=h['x'], cy=h['y'], r=h['d'] / 2 + (HOLE_CLEAR - CLEAR))
            g.add_copper(s, [0, 1], -2)
            g.add_drill(h['x'], h['y'], h['d'] / 2)
        for t in self.data.get('tracks', []):
            net = self.netid[t['net']]
            g.add_copper(Shape('seg', x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], r=t['w'] / 2),
                         [t['layer']], net)
        for v in self.data.get('vias', []):
            net = self.netid[v['net']]
            g.add_copper(Shape('circle', cx=v['x'], cy=v['y'], r=VIA_D / 2), [0, 1], net)
            g.add_drill(v['x'], v['y'], VIA_DRILL / 2)
        return g

    # -- komórki padu dostępne dla danej sieci i szerokości
    def pad_cells(self, g, shape, layers, net, need):
        cells = []
        for L in layers:
            for i, px, py in g.cells_near(shape.bb, 0.0):
                if shape.dist(px, py) <= 1e-6 and self.ok(g, L, i, net, need):
                    cells.append(L * g.N + i)
        if not cells:     # pad mniejszy niż oczko siatki: najbliższa dopuszczalna komórka
            cx = (shape.bb[0] + shape.bb[2]) / 2
            cy = (shape.bb[1] + shape.bb[3]) / 2
            best = None
            for L in layers:
                for i, px, py in g.cells_near(shape.bb, GRID):
                    if self.ok(g, L, i, net, need):
                        d = math.hypot(px - cx, py - cy)
                        if d <= GRID * 0.75 and (best is None or d < best[0]):
                            best = (d, L * g.N + i)
            if best:
                cells.append(best[1])
                self.fallback[best[1]] = (cx, cy)
        return cells

    def ok(self, g, L, i, net, need):
        return g.foreign(L, i, net) >= need - 1e-6 and g.edge[i] >= EDGE_CLEAR + (need - CLEAR) - 1e-6

    def via_ok(self, g, i, net):
        need = CLEAR + VIA_D / 2
        return (g.foreign(0, i, net) >= need - 1e-6 and g.foreign(1, i, net) >= need - 1e-6
                and g.pad_any[0][i] >= VIA_D / 2 + 0.05 and g.pad_any[1][i] >= VIA_D / 2 + 0.05
                and g.drill[i] >= HOLE2HOLE + VIA_DRILL / 2 and g.edge[i] >= EDGE_CLEAR + VIA_D / 2)

    def astar(self, g, sources, targets, net, need, tx, ty, max_steps=250000):
        nx, N = g.nx, g.N
        okc = {}

        def legal(s):
            v = okc.get(s)
            if v is None:
                L, i = divmod(s, N)
                v = okc[s] = self.ok(g, L, i, net, need)
            return v

        def h(s):
            i = s % N
            x, y = (i % nx), (i // nx)
            best = INF
            for (ax, ay) in tx:
                dx, dy = abs(x - ax), abs(y - ay)
                v = (dx + dy) + (SQ2 - 2) * min(dx, dy)
                if v < best:
                    best = v
            return best

        gcost = {}
        parent = {}
        heap = []
        for s in sources:
            gcost[s] = 0.0
            parent[s] = -1
            heapq.heappush(heap, (h(s), 0.0, s))
        tset = targets
        steps = 0
        moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
        while heap:
            f, gc, s = heapq.heappop(heap)
            if gc > gcost.get(s, INF):
                continue
            if s in tset:
                path = []
                while s != -1:
                    path.append(s)
                    s = parent[s]
                return path[::-1]
            steps += 1
            if steps > max_steps:
                return None
            L, i = divmod(s, N)
            ix, iy = i % nx, i // nx
            base = L * N
            pad_any, pad_net = g.pad_any[L], g.pad_net[L]
            for dx, dy, c in moves:
                jx, jy = ix + dx, iy + dy
                if jx < 0 or jy < 0 or jx >= nx or jy >= g.ny:
                    continue
                j = base + jy * nx + jx
                if not legal(j):
                    continue
                if dx and dy and not (legal(base + iy * nx + jx) and legal(base + jy * nx + ix)):
                    continue
                # preferencja kierunku: wierzch poziomo, spód pionowo (lekka kara)
                cc = c * (1.25 if (L == 0 and dx == 0) or (L == 1 and dy == 0) else 1.0)
                k = j - base
                if pad_any[k] < PAD_KEEP and pad_net[k] != net:
                    cc += PAD_PENALTY
                ng = gc + cc
                if ng < gcost.get(j, INF):
                    gcost[j] = ng
                    parent[j] = s
                    heapq.heappush(heap, (ng + h(j) * 1.15, ng, j))
            # przelotka
            o = (1 - L) * N + i
            if legal(o) and self.via_ok(g, i, net):
                ng = gc + VIA_COST
                if ng < gcost.get(o, INF):
                    gcost[o] = ng
                    parent[o] = s
                    heapq.heappush(heap, (ng + h(o) * 1.15, ng, o))
        return None

    def via_stub(self, g, gr, net, need, w, name, result):
        """Najbliższe miejsce na przelotkę osiągalne z padu (do 3 mm) – połączenie z wylewką."""
        N = g.N
        best = None
        cx, cy = gr['pad']['x'], gr['pad']['y']
        r = int(3.0 / GRID)
        ix0, iy0 = int(round(cx / GRID)), int(round(cy / GRID))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                jx, jy = ix0 + dx, iy0 + dy
                if 0 <= jx < g.nx and 0 <= jy < g.ny:
                    j = jy * g.nx + jx
                    d = math.hypot(dx, dy)
                    if (best is None or d < best[0]) and self.via_ok(g, j, net):
                        best = (d, j)
        if best is None:
            return False
        j = best[1]
        tgt = {L * N + j for L in (0, 1)}
        vx, vy = g.xy(j)
        path = self.astar(g, gr['cells'], tgt, net, need, [(j % g.nx, j // g.nx)], None)
        if path is None:
            return False
        segs, vias = self.path_to_geometry(g, path, w)
        if (round(vx, 4), round(vy, 4)) not in vias:
            vias.append((round(vx, 4), round(vy, 4)))
        for sg in segs:
            sg['net'] = name
            result['tracks'].append(sg)
            g.add_copper(Shape('seg', x1=sg['x1'], y1=sg['y1'], x2=sg['x2'], y2=sg['y2'], r=w / 2), [sg['layer']], net)
        for (x, y) in vias:
            result['vias'].append(dict(x=x, y=y, net=name))
            g.add_copper(Shape('circle', cx=x, cy=y, r=VIA_D / 2), [0, 1], net)
            g.add_drill(x, y, VIA_DRILL / 2)
        result.setdefault('plane_stubs', []).append('%s.%s' % (gr['pad']['ref'], gr['pad']['num']))
        return True

    def path_to_geometry(self, g, path, w):
        segs, vias = [], []
        N = g.N
        pts = []
        for s in path:
            L, i = divmod(s, N)
            x, y = g.xy(i)
            pts.append((L, round(x, 4), round(y, 4)))
        run = [pts[0]]
        for p in pts[1:]:
            if p[0] != run[-1][0]:
                vias.append((p[1], p[2]))
                segs += self._merge(run, w)
                run = [p]
            else:
                run.append(p)
        segs += self._merge(run, w)
        return segs, vias

    @staticmethod
    def _merge(run, w):
        out = []
        if len(run) < 2:
            return out
        L = run[0][0]
        start = run[0]
        prev = run[0]
        d = None
        for p in run[1:]:
            nd = (round((p[1] - prev[1]) / GRID), round((p[2] - prev[2]) / GRID))
            if d is not None and nd != d:
                out.append(dict(layer=L, x1=start[1], y1=start[2], x2=prev[1], y2=prev[2], w=w))
                start = prev
            d = nd
            prev = p
        out.append(dict(layer=L, x1=start[1], y1=start[2], x2=prev[1], y2=prev[2], w=w))
        return out

    def route_all(self, order):
        g = self.build_static()
        result = dict(tracks=[], vias=[], failed=[])
        by_net = {}
        for p, s, net in self.pads:
            if p['net']:
                by_net.setdefault(p['net'], []).append((p, s))
        pre_tree = {}
        for t in self.data.get('tracks', []):
            pre_tree.setdefault(t['net'], []).append(t)
        stubbed = set()
        for name in order:
            net = self.netid[name]
            w = self.width[name]
            need = CLEAR + w / 2
            pads = by_net.get(name, [])
            if len(pads) < 2:
                continue
            # grupy: pady (nachodzące na siebie łączą się) + ścieżki wstępne dołączone do padów
            groups = []
            pre = []
            for t in pre_tree.get(name, []):
                # tylko wolny koniec (x2, y2) – inaczej reszta odcinka zostałaby „wisząca”
                i = g.idx(int(round(t['x2'] / GRID)), int(round(t['y2'] / GRID)))
                pre.append(dict(pad=None, cells={t['layer'] * g.N + i}, track=t))
            for p, sh in pads:
                cells = self.pad_cells(g, sh, p['layers'], net, need)
                if not cells:
                    fed = [q for q in pre if sh.dist(q['track']['x1'], q['track']['y1']) <= 1e-6
                           or sh.dist(q['track']['x2'], q['track']['y2']) <= 1e-6]
                    if fed:
                        fed[0]['pad'] = p
                        continue
                    result['failed'].append(dict(net=name, pad='%s.%s' % (p['ref'], p['num']), why='brak dostępu'))
                    continue
                groups.append(dict(pad=p, cells=set(cells)))
            groups += pre
            merged = True
            while merged:
                merged = False
                for a in range(len(groups)):
                    for b in range(a + 1, len(groups)):
                        if groups[a]['cells'] & groups[b]['cells']:
                            groups[a]['cells'] |= groups[b]['cells']
                            if groups[a]['pad'] is None:
                                groups[a]['pad'] = groups[b]['pad']
                            del groups[b]
                            merged = True
                            break
                    if merged:
                        break
            groups = [gr for gr in groups if gr['pad'] is not None]
            if len(groups) < 2:
                continue
            tree = set(groups[0]['cells'])
            rest = groups[1:]
            while rest:
                tcells = set()
                tx = []
                for gr in rest:
                    tcells |= gr['cells']
                    tx.append((round(gr['pad']['x'] / GRID), round(gr['pad']['y'] / GRID)))
                path = self.astar(g, tree, tcells, net, need, tx, None)
                if path is None and name in self.plane_nets:
                    # żaden z pozostałych padów nie dosięga drzewa: każdy dostaje przelotkę do wylewki
                    for gr in rest:
                        if not self.via_stub(g, gr, net, need, w, name, result):
                            result['failed'].append(dict(net=name, pad='%s.%s' % (gr['pad']['ref'], gr['pad']['num']),
                                                         why='brak trasy i miejsca na przelotkę'))
                    break
                if path is None:
                    for gr in rest:
                        result['failed'].append(dict(net=name, pad='%s.%s' % (gr['pad']['ref'], gr['pad']['num']),
                                                     why='brak trasy'))
                    break
                segs, vias = self.path_to_geometry(g, path, w)
                for end_cell in (path[0], path[-1]):
                    if end_cell in self.fallback and end_cell not in stubbed:
                        stubbed.add(end_cell)
                        L, i = divmod(end_cell, g.N)
                        x, y = g.xy(i)
                        px, py = self.fallback[end_cell]
                        segs.append(dict(layer=L, x1=round(x, 4), y1=round(y, 4), x2=px, y2=py, w=min(w, 0.25)))
                for sg in segs:
                    sg['net'] = name
                    result['tracks'].append(sg)
                    sh = Shape('seg', x1=sg['x1'], y1=sg['y1'], x2=sg['x2'], y2=sg['y2'], r=w / 2)
                    g.add_copper(sh, [sg['layer']], net)
                for (vx, vy) in vias:
                    result['vias'].append(dict(x=vx, y=vy, net=name))
                    g.add_copper(Shape('circle', cx=vx, cy=vy, r=VIA_D / 2), [0, 1], net)
                    g.add_drill(vx, vy, VIA_DRILL / 2)
                tree |= set(path)
                end = path[-1]
                hit = [gr for gr in rest if end in gr['cells']]
                for gr in hit:
                    tree |= gr['cells']
                    rest.remove(gr)
                # komórki nowej miedzi (szersze ścieżki) też należą do drzewa
                for sg in segs:
                    sh = Shape('seg', x1=sg['x1'], y1=sg['y1'], x2=sg['x2'], y2=sg['y2'], r=w / 2)
                    for i, px, py in g.cells_near(sh.bb, 0.0):
                        if sh.dist(px, py) <= 1e-6 and self.ok(g, sg['layer'], i, net, need):
                            tree.add(sg['layer'] * g.N + i)
        return result

def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = json.load(open(src))
    r = Router(data)
    order = [n['name'] for n in data['nets']]
    fails = {}
    best = None
    for it in range(int(data.get('iterations', 4))):
        t0 = time.time()
        res = r.route_all(order)
        failed_nets = []
        for f in res['failed']:
            if f['net'] not in failed_nets:
                failed_nets.append(f['net'])
        print('przebieg %d: %d ścieżek, %d przelotek, nieudane: %s (%.1f s)'
              % (it + 1, len(res['tracks']), len(res['vias']), failed_nets or '—', time.time() - t0))
        sys.stdout.flush()
        if best is None or len(res['failed']) < len(best['failed']):
            best = res
        if not res['failed']:
            break
        for n in failed_nets:
            fails[n] = fails.get(n, 0) + 1
        base = [n['name'] for n in data['nets']]
        order = sorted(base, key=lambda n: (-fails.get(n, 0), base.index(n)))
    json.dump(best, open(dst, 'w'), indent=0)
    for f in best['failed']:
        print('  NIEUDANE', f)


if __name__ == '__main__':
    main()
