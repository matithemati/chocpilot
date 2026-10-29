"""Generuje chocpilot-v2.kicad_pcb z design.py (uruchamiać Pythonem KiCad – moduł pcbnew).

  python3(KiCad) gen_pcb.py            – rozmieszczenie, trasowanie (router.py), strefy GND
  python3(KiCad) gen_pcb.py --reuse    – jak wyżej, ale z zapisanych wyników trasowania

Footprinty są powiązane z symbolami schematu (ta sama ścieżka UUID co w gen_sch.py), więc
„Update PCB from Schematic” i test zgodności DRC widzą jeden projekt.
"""
import json
import math
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
from gen_sch import uid  # noqa: E402
from sexpr import find, find1, parse  # noqa: E402

PRJ = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(PRJ, 'chocpilot-v2.kicad_pcb')
WORK = os.path.join(HERE, 'build')
STOCK = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'
OX, OY = design.BOARD_ORIGIN
MM = pcbnew.FromMM


def P(x, y):
    """Współrzędne płytki (mm, róg płytki = 0,0) → KiCad."""
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def lib_path(lib):
    if lib == 'chocpilot':
        return os.path.join(PRJ, 'chocpilot.pretty')
    return STOCK + lib + '.pretty'


# ---------------------------------------------------------------- netlista ze schematu
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def read_netlist():
    """Nazwy sieci i pola symboli dokładnie tak, jak widzi je KiCad (np. „/K1”)."""
    path = os.path.join(WORK, 'chocpilot-v2.net')
    subprocess.check_call([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', path,
                           os.path.join(PRJ, 'chocpilot-v2.kicad_sch')],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    root = parse(open(path).read())
    pin_net, fields = {}, {}
    for comp in find(find1(root, 'components'), 'comp'):
        ref = find1(comp, 'ref')[1]
        fields[ref] = {find1(p, 'name')[1]: find1(p, 'value')[1] for p in find(comp, 'property')
                       if find1(p, 'value') is not None}        # bez wartości = flagi (np. dnp)
        for key in ('datasheet', 'description'):
            node = find1(comp, key)
            if node is not None:
                fields[ref][key.capitalize()] = node[1]
    for net in find(find1(root, 'nets'), 'net'):
        name = find1(net, 'name')[1]
        for node in find(net, 'node'):
            pin_net[(find1(node, 'ref')[1], find1(node, 'pin')[1])] = name
    # kontrola: podział na sieci identyczny jak w design.py
    alias = {}
    for dn, nodes in design.nets().items():
        kn = {pin_net[n] for n in nodes}
        if len(kn) != 1:
            raise SystemExit('sieć %s rozbita na schemacie: %s' % (dn, kn))
        alias[dn] = kn.pop()
    if len(set(alias.values())) != len(alias):
        raise SystemExit('dwie sieci design.py połączone na schemacie')
    return pin_net, fields, alias


# ---------------------------------------------------------------- budowa płytki
def build_board(pin_net, fields):
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    nets = {}
    for name in sorted(set(pin_net.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # obrys z zaokrąglonymi narożnikami
    W, H, R = design.BOARD_W, design.BOARD_H, design.CORNER_R
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(c, a0):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        pts = [(c[0] + R * math.cos(math.radians(a)), c[1] + R * math.sin(math.radians(a)))
               for a in (a0, a0 + 45, a0 + 90)]
        s.SetArcGeometry(P(*pts[0]), P(*pts[1]), P(*pts[2]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    seg((R, 0), (W - R, 0))
    seg((W, R), (W, H - R))
    seg((W - R, H), (R, H))
    seg((0, H - R), (0, R))
    arc((W - R, R), 270)
    arc((W - R, H - R), 0)
    arc((R, H - R), 90)
    arc((R, R), 180)

    fps = {}
    for p in design.parts:
        lib, name = p['fp'].split(':')
        fp = pcbnew.FootprintLoad(lib_path(lib), name)
        if fp is None:
            raise SystemExit('brak footprintu ' + p['fp'])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(p['ref'])
        fp.SetValue(p['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + uid('sym', p['ref'])))
        fp.SetSheetname('/')
        fp.SetSheetfile('chocpilot-v2.kicad_sch')
        x, y, rot, side = p['pcb']
        fp.SetPosition(P(x, y))
        board.Add(fp)                # Flip wymaga footprintu na płytce
        if side == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        if p['dnp']:
            fp.SetDNP(True)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num and (p['ref'], num) in pin_net:
                pad.SetNet(nets[pin_net[(p['ref'], num)]])
            elif num and p['pins']:
                raise SystemExit('%s: pad %s nie ma pinu w symbolu' % (p['ref'], num))
        for name, val in fields.get(p['ref'], {}).items():
            if name in ('Reference', 'Value', 'Footprint'):
                continue
            if name == 'ki_fp_filters':      # w KiCad 10 atrybut footprintu, nie pole
                fp.SetFilters(val)
                continue
            if name.startswith('ki_'):
                continue
            fp.SetField(name, val)
            f = fp.GetField(name)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab if side == 'F' else pcbnew.B_Fab)
        fps[p['ref']] = fp

    # opisy na sitodruku
    def text(s, x, y, layer, size=1.5, mirror=False):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(size * 0.15))
        if mirror:
            t.SetMirrored(True)
        board.Add(t)

    text('ChocPilot v2', 34.0, 44.0, pcbnew.B_SilkS, 1.5, mirror=True)
    text('rev 2.0  2026-10', 34.0, 46.5, pcbnew.B_SilkS, 1.0, mirror=True)
    text('RESET', 46.0, 65.2, pcbnew.B_SilkS, 1.0, mirror=True)
    text('BOOT0', 58.0, 65.2, pcbnew.B_SilkS, 1.0, mirror=True)
    j2 = design.XC - 3.81
    for i, name in enumerate(['GND', 'VCC', 'SCL', 'SDA']):
        text(name, j2 + i * 2.54, design.OLED_PIN_Y - 2.0, pcbnew.F_SilkS, 0.8)
    for i, name in enumerate(['3V3', 'DIO', 'CLK', 'RST', 'GND']):
        text(name, 72.0 + i * 2.54, 60.3, pcbnew.F_SilkS, 0.8)
    jp = [p for p in design.parts if p['ref'] == 'JP1'][0]['pcb']
    text('3V3', jp[0] - 1.3, jp[1] - 1.6, pcbnew.F_SilkS, 0.8)
    text('5V', jp[0] + 1.3, jp[1] - 1.6, pcbnew.F_SilkS, 0.8)
    place_refs(board, fps)
    return board, nets, fps


# ---------------------------------------------------------------- oznaczenia na sitodruku
KEEP_REF = ('S', 'ENC', 'RV', 'J1', 'U1')     # duże elementy: oznaczenie z biblioteki


def _box(bb, m=0.0):
    return (pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m,
            pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m)


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _seg_boxes(item, m):
    """Linie sitodruku jako cienkie prostokąty (obrys elementu nie blokuje swojego wnętrza)."""
    st = item.GetShape() if hasattr(item, 'GetShape') else None
    pts = []
    if st == pcbnew.SHAPE_T_SEGMENT:
        pts = [(item.GetStart(), item.GetEnd())]
    elif st == pcbnew.SHAPE_T_RECTANGLE:
        c = item.GetRectCorners()
        pts = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    elif st == pcbnew.SHAPE_T_POLY:
        ol = item.GetPolyShape().Outline(0)
        n = ol.PointCount()
        pts = [(ol.CPoint(i), ol.CPoint((i + 1) % n)) for i in range(n)]
    if not pts:
        return [_box(item.GetBoundingBox(), m)]
    out = []
    for a, b in pts:
        out.append((pcbnew.ToMM(min(a.x, b.x)) - m, pcbnew.ToMM(min(a.y, b.y)) - m,
                    pcbnew.ToMM(max(a.x, b.x)) + m, pcbnew.ToMM(max(a.y, b.y)) + m))
    return out


def place_refs(board, fps):
    """Oznaczenia małych elementów: pierwsze wolne miejsce wokół obrysu (góra, dół, boki)."""
    obst = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
    cu = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}
    for fp in fps.values():
        for pad in fp.Pads():
            for silk, lid in cu.items():
                if pad.IsOnLayer(lid) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    obst[silk].append(_box(pad.GetBoundingBox(), 0.2))
        for item in fp.GraphicalItems():
            if item.GetLayer() in obst:
                if item.GetClass() in ('PCB_TEXT', 'PCB_FIELD'):
                    obst[item.GetLayer()].append(_box(item.GetBoundingBox(), 0.15))
                else:
                    obst[item.GetLayer()] += _seg_boxes(item, 0.15)
    for d in board.Drawings():
        if d.GetLayer() in obst:
            obst[d.GetLayer()].append(_box(d.GetBoundingBox(), 0.15))
    fixed = [r for r in fps if r.startswith(KEEP_REF) and not r.startswith('SW')]
    for r in fixed:
        f = fps[r].Reference()
        if abs(fps[r].GetOrientationDegrees()) == 180:
            f.SetTextAngleDegrees(0)       # footprint obrócony o 180°: tekst z powrotem czytelny
        if f.IsVisible() and f.GetLayer() in obst:
            obst[f.GetLayer()].append(_box(f.GetBoundingBox(), 0.15))
    lim = (OX + 0.4, OY + 0.4, OX + design.BOARD_W - 0.4, OY + design.BOARD_H - 0.4)
    for ref in sorted(fps):
        if ref in fixed:
            continue
        fp = fps[ref]
        f = fp.Reference()
        f.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        f.SetTextThickness(MM(0.12))
        layer = f.GetLayer()
        cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
        bb = _box(cy.BBox()) if cy.OutlineCount() else _box(fp.GetBoundingBox(False))
        cx, cyy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        cands = []
        for gap in (0.55, 1.1, 1.8):
            cands += [(cx, bb[1] - gap, 0), (cx, bb[3] + gap, 0),
                      (bb[0] - gap, cyy, 90), (bb[2] + gap, cyy, 90),
                      (bb[0] - gap - 1.0, cyy, 0), (bb[2] + gap + 1.0, cyy, 0)]
        placed = False
        for x, y, ang in cands:
            f.SetTextAngleDegrees(ang)
            f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            tb = _box(f.GetBoundingBox())
            # przesunięcie o pół wymiaru tekstu od obrysu
            if ang == 0 and y < bb[1]:
                y -= (tb[3] - tb[1]) / 2
            elif ang == 0 and y > bb[3]:
                y += (tb[3] - tb[1]) / 2
            elif ang == 90 and x < bb[0]:
                x -= (tb[2] - tb[0]) / 2
            elif ang == 90:
                x += (tb[2] - tb[0]) / 2
            elif x < bb[0]:
                x -= (tb[2] - tb[0]) / 2 - 1.0
            else:
                x += (tb[2] - tb[0]) / 2 - 1.0
            f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            tb = _box(f.GetBoundingBox())
            if not (lim[0] < tb[0] and tb[2] < lim[2] and lim[1] < tb[1] and tb[3] < lim[3]):
                continue
            if any(_hit(tb, o) for o in obst[layer]):
                continue
            obst[layer].append((tb[0] - 0.15, tb[1] - 0.15, tb[2] + 0.15, tb[3] + 0.15))
            placed = True
            break
        if not placed:
            f.SetVisible(False)
            print('  oznaczenie ukryte (brak miejsca):', ref)


# ---------------------------------------------------------------- dane dla routera
def to_local(v):
    return pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY


def export_geometry(board, fps, pre_tracks, alias):
    pads, holes = [], []
    shape_name = {pcbnew.PAD_SHAPE_CIRCLE: 'circle', pcbnew.PAD_SHAPE_OVAL: 'oval'}
    for ref, fp in fps.items():
        for pad in fp.Pads():
            x, y = to_local(pad.GetPosition())
            attr = pad.GetAttribute()
            drill = pad.GetDrillSize()
            if attr == pcbnew.PAD_ATTRIB_NPTH:
                holes.append(dict(x=x, y=y, d=pcbnew.ToMM(max(drill.x, drill.y))))
                continue
            layers = [L for L, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(lid)]
            lid = pcbnew.F_Cu if 0 in layers else pcbnew.B_Cu
            shape = shape_name.get(pad.GetShape(lid), 'rect')
            if shape == 'rect':          # prostokąty, zaokrąglone i własne: obrys padu
                bb = pad.GetBoundingBox()
                x, y = to_local(bb.GetCenter())
                w, h, rot = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), 0
            else:
                sz = pad.GetSize(lid)
                w, h, rot = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y), pad.GetOrientationDegrees()
            pads.append(dict(ref=ref, num=pad.GetNumber(), net=pad.GetNetname() or None,
                             x=x, y=y, w=w, h=h, rot=rot, shape=shape, layers=layers,
                             drill=pcbnew.ToMM(max(drill.x, drill.y)) if attr == pcbnew.PAD_ATTRIB_PTH else 0))
        for item in fp.GraphicalItems():   # miedź narysowana w footprincie (np. mostek zworki)
            for L, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                if item.GetLayer() == lid:
                    bb = item.GetBoundingBox()
                    x, y = to_local(bb.GetCenter())
                    pads.append(dict(ref=ref, num='', net=None, x=x, y=y, w=pcbnew.ToMM(bb.GetWidth()),
                                     h=pcbnew.ToMM(bb.GetHeight()), rot=0, shape='rect', layers=[L], drill=0))
    return dict(board=dict(w=design.BOARD_W, h=design.BOARD_H, corner=design.CORNER_R),
                pads=pads, holes=holes, tracks=pre_tracks, vias=[], nets=route_order(alias), iterations=12,
                plane_nets=['GND'])


def route_order(alias):
    nets = design.nets()
    first = ['USB_CONN_DP', 'USB_CONN_DN', 'USB_DP', 'USB_DN', 'CC1', 'CC2', 'OSC_IN', 'OSC_OUT',
             'VBUS', '+5V', '+3V3']
    pos = {p['ref']: p['pcb'] for p in design.parts}

    def span(n):
        xs = [pos[r][0] for r, _ in nets[n]]
        ys = [pos[r][1] for r, _ in nets[n]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    rest = sorted((n for n in nets if n not in first and n != 'GND'), key=span)
    out = []
    for n in first + rest + ['GND']:
        if n in nets:
            out.append(dict(name=alias[n], width=design.NET_WIDTH.get(n, design.DEFAULT_WIDTH)))
    return out


def usb_prerouting(fps):
    """Krótkie odcinki przy USB-C, których router siatkowy nie trafi w raster 0,5 mm."""
    fp = fps['J1']
    pad = {}
    for p in fp.Pads():
        pad.setdefault(p.GetNumber(), []).append(to_local(p.GetPosition()))
    tracks = []
    for num in ('A4', 'A9'):        # VBUS: wyjście prosto w głąb płytki, szerokie
        x, y = pad[num][0]
        tracks.append(dict(net='VBUS', layer=0, x1=x, y1=y, x2=x, y2=y + 2.4, w=0.6))
    sh = sorted(pad['SH'], key=lambda q: -q[1])[:2]   # dwa kołki ekranu bliżej padów
    for num in ('A1', 'B1'):        # GND padów → kołek ekranu (THT, obie warstwy)
        x, y = pad[num][0]
        sx, sy = min(sh, key=lambda q: abs(q[0] - x))
        tracks.append(dict(net='GND', layer=0, x1=x, y1=y, x2=sx, y2=y, w=0.3))
    return tracks


# ---------------------------------------------------------------- trasy i strefy
def apply_routes(board, nets, routes, pre_tracks):
    for t in pre_tracks + routes['tracks']:
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(P(t['x1'], t['y1']))
        tr.SetEnd(P(t['x2'], t['y2']))
        tr.SetWidth(MM(t['w']))
        tr.SetLayer(pcbnew.F_Cu if t['layer'] == 0 else pcbnew.B_Cu)
        tr.SetNet(nets[t['net']])
        board.Add(tr)
    for v in routes['vias']:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(P(v['x'], v['y']))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetWidth(MM(0.6))
        via.SetDrill(MM(0.3))
        via.SetNet(nets[v['net']])
        board.Add(via)


def add_zones(board, nets):
    W, H = design.BOARD_W, design.BOARD_H
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets['GND'])
        z.SetZoneName('GND_' + ('F' if layer == pcbnew.F_Cu else 'B'))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            ol.Append(MM(OX + x), MM(OY + y))
        z.SetLocalClearance(MM(0.3))
        z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(0)
        board.Add(z)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def main():
    os.makedirs(WORK, exist_ok=True)
    pin_net, fields, alias = read_netlist()
    board, nets, fps = build_board(pin_net, fields)
    pre = usb_prerouting(fps)
    geo = export_geometry(board, fps, pre, alias)
    gin = os.path.join(WORK, 'route_in.json')
    gout = os.path.join(WORK, 'route_out.json')
    json.dump(geo, open(gin, 'w'), indent=0)
    if '--place-only' in sys.argv:
        routes = dict(tracks=[], vias=[], failed=[])
    else:
        if '--reuse' not in sys.argv or not os.path.exists(gout):
            subprocess.check_call(['/usr/local/bin/python3', os.path.join(HERE, 'router.py'), gin, gout])
        routes = json.load(open(gout))
    apply_routes(board, nets, routes, pre)
    if '--place-only' not in sys.argv:
        add_zones(board, nets)
    pcbnew.SaveBoard(OUT, board, True)
    print('zapisano', OUT, '| nieudane połączenia:', len(routes['failed']))


if __name__ == '__main__':
    main()
