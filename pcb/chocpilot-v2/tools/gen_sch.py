"""Generuje chocpilot-v2.kicad_sch z design.py.

Każdy pin dostaje krótki odcinek przewodu zakończony etykietą sieci (sygnały) albo
symbolem zasilania (GND, +3V3, +5V, VBUS). Piny niepodłączone dostają znacznik „no connect”.
Symbole kopiowane są z bibliotek KiCad (symbole pochodne – „extends” – są spłaszczane).
"""
import copy
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
from sexpr import Sym, dump, find, find1, parse  # noqa: E402

SYMDIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/'
OUT = os.path.join(os.path.dirname(__file__), '..', 'chocpilot-v2.kicad_sch')
PROJECT = 'chocpilot-v2'
POWER_NETS = {'GND': 'power:GND', '+3V3': 'power:+3V3', '+5V': 'power:+5V', 'VBUS': 'power:VBUS'}
STUB = 2.54

# deterministyczne UUID – kolejne generowania dają ten sam plik
_NS = uuid.UUID('7d0c3c58-3b0e-4a43-9a43-1f2d1c0c2a77')


def uid(*key):
    return str(uuid.uuid5(_NS, '/'.join(str(k) for k in key)))


ROOT_UUID = uid('root')
_libs = {}


def lib_symbol(lib_id):
    """Zwraca spłaszczony symbol biblioteczny nazwany pełnym lib_id."""
    lib, name = lib_id.split(':')
    if lib not in _libs:
        root = parse(open(SYMDIR + lib + '.kicad_sym').read())
        _libs[lib] = {s[1]: s for s in find(root, 'symbol')}
    syms = _libs[lib]

    def flat(n):
        s = copy.deepcopy(syms[n])
        ext = find1(s, 'extends')
        if not ext:
            return s
        parent = flat(ext[1])
        props = {p[1]: p for p in find(s, 'property')}
        out = [Sym('symbol'), n]
        for c in parent[2:]:
            if isinstance(c, list) and c[0] == 'property' and c[1] in props:
                out.append(props.pop(c[1]))
            elif isinstance(c, list) and c[0] == 'symbol':
                sub = copy.deepcopy(c)
                sub[1] = n + sub[1][len(parent[1]):]
                out.append(sub)
            else:
                out.append(copy.deepcopy(c))
        # pozostałe właściwości dziecka wstaw przed pierwszym pod-symbolem
        idx = next(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == 'symbol')
        for p in props.values():
            out.insert(idx, p)
            idx += 1
        return out

    s = flat(name)
    s[1] = lib_id
    return s


def sym_pins(libsym):
    pins = []
    for u in find(libsym, 'symbol'):
        parts = str(u[1]).split('_')
        unit, style = int(parts[-2]), int(parts[-1])
        if unit not in (0, 1) or style not in (0, 1):
            continue
        for p in find(u, 'pin'):
            at = find1(p, 'at')
            pins.append(dict(num=find1(p, 'number')[1], x=float(at[1]), y=float(at[2]),
                             ang=int(float(at[3])) if len(at) > 3 else 0, type=str(p[1])))
    return pins


def r2(v):
    return round(v * 100) / 100


# ---------------------------------------------------------------- rozmieszczenie na arkuszu A3
G = 2.54


def _sch_layout():
    pos = {
        # USB i zasilanie
        'J1': (40.64, 66.04), 'F1': (93.98, 50.8), 'R1': (81.28, 83.82), 'R2': (91.44, 83.82),
        'U3': (121.92, 76.2), 'U2': (132.08, 50.8),
        'C1': (104.14, 50.8), 'C2': (114.3, 63.5), 'C4': (152.4, 63.5), 'C3': (162.56, 50.8),
        # MCU i otoczenie
        'U1': (236.22, 134.62),
        'C5': (152.4, 106.68), 'C6': (162.56, 106.68), 'C7': (172.72, 106.68),
        'C8': (182.88, 106.68), 'C9': (193.04, 106.68),
        'C10': (152.4, 129.54), 'C11': (162.56, 129.54), 'C12': (180.34, 129.54),
        'R3': (190.5, 129.54),
        'Y1': (165.1, 152.4), 'C13': (154.94, 165.1), 'C14': (175.26, 165.1),
        'SW1': (292.1, 104.14), 'SW2': (292.1, 116.84), 'J3': (325.12, 104.14),
        # OLED
        'JP1': (264.16, 50.8), 'C15': (281.94, 63.5), 'R4': (292.1, 63.5), 'R5': (302.26, 63.5),
        'J2': (325.12, 50.8),
        # enkodery, suwak
        'ENC1': (365.76, 55.88), 'ENC2': (365.76, 83.82), 'RV1': (360.68, 114.3), 'C16': (381.0, 114.3),
        # konwerter poziomu LED
        'U4': (302.26, 157.48), 'C17': (327.66, 157.48), 'R6': (340.36, 157.48), 'C18': (353.06, 157.48),
    }
    for i in range(8):
        row, col = divmod(i, 4)
        pos['S%d' % (i + 1)] = (35.56 + col * 27.94, 124.46 + row * 22.86)
    for i in range(design.N_LED):
        x, y = 38.1 + (i % 6) * 43.18, 215.9 + (i // 6) * 35.56
        pos['L%d' % (i + 1)] = (x, y)
        pos['C%d' % (19 + i)] = (x + 21.59, y)
    for i in range(4):
        pos['H%d' % (i + 1)] = (375.92 + (i % 2) * 15.24, 152.4 + (i // 2) * 12.7)
    return pos


SCH_POS = _sch_layout()

items = []
lib_cache = {}
pwr_count = [0]


def effects(size=1.27, justify=None, hide=False):
    e = [Sym('effects'), [Sym('font'), [Sym('size'), size, size]]]
    if justify:
        e.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym('hide'), Sym('yes')])
    return e


def prop(name, value, x, y, hide=False, ang=0, justify=None):
    p = [Sym('property'), name, value, [Sym('at'), r2(x), r2(y), ang]]
    if hide:
        p.append([Sym('hide'), Sym('yes')])
    p.append(effects(justify=justify))
    return p


def place_symbol(lib_id, ref, value, x, y, rot=0, footprint='', fields=None, dnp=False,
                 in_bom=True, on_board=True, key=None):
    if lib_id not in lib_cache:
        lib_cache[lib_id] = lib_symbol(lib_id)
    ls = lib_cache[lib_id]
    key = key or ref
    flag = find1(ls, 'in_bom')
    if in_bom and flag is not None and str(flag[1]) == 'no':
        in_bom = False             # np. otwory montażowe, zworki lutowane
    node = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), r2(x), r2(y), rot],
            [Sym('unit'), 1], [Sym('exclude_from_sim'), Sym('no')],
            [Sym('in_bom'), Sym('yes' if in_bom else 'no')],
            [Sym('on_board'), Sym('yes' if on_board else 'no')],
            [Sym('dnp'), Sym('yes' if dnp else 'no')],
            [Sym('uuid'), uid('sym', key)]]
    for lp in find(ls, 'property'):
        name = lp[1]
        if name.startswith('ki_'):       # słowa kluczowe i filtry zostają tylko w lib_symbols
            continue
        at = find1(lp, 'at')
        hide = bool(find1(lp, 'hide')) or name not in ('Reference', 'Value')
        val = {'Reference': ref, 'Value': value, 'Footprint': footprint}.get(name, lp[2])
        if rot == 180:
            px, py = x - float(at[1]), y + float(at[2])
        else:
            px, py = x + float(at[1]), y - float(at[2])
        node.append(prop(name, val, px, py, hide=hide, ang=int(float(at[3])) if len(at) > 3 else 0))
    for k, v in (fields or {}).items():
        node.append(prop(k, v, x, y, hide=True))
    for p in sym_pins(ls):
        node.append([Sym('pin'), p['num'], [Sym('uuid'), uid('pin', key, p['num'])]])
    node.append([Sym('instances'), [Sym('project'), PROJECT,
                 [Sym('path'), '/' + ROOT_UUID, [Sym('reference'), ref], [Sym('unit'), 1]]]])
    items.append(node)
    return ls


_points = {}


def mark(net, x, y):
    k = (round(x / 1.27), round(y / 1.27))
    if _points.setdefault(k, net) != net:
        raise SystemExit('zwarcie na schemacie w (%.2f, %.2f): %s i %s' % (x, y, _points[k], net))


def mark_wire(net, x1, y1, x2, y2):
    n = int(round(max(abs(x2 - x1), abs(y2 - y1)) / 1.27))
    for i in range(n + 1):
        t = i / n if n else 0
        mark(net, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)


def wire(x1, y1, x2, y2):
    items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), r2(x1), r2(y1)], [Sym('xy'), r2(x2), r2(y2)]],
                  [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]],
                  [Sym('uuid'), uid('wire', x1, y1, x2, y2)]])


def label(name, x, y, d):
    ang, just = {(-1, 0): (180, 'right bottom'), (1, 0): (0, 'left bottom'),
                 (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}[d]
    items.append([Sym('label'), name, [Sym('at'), r2(x), r2(y), ang], effects(justify=just),
                  [Sym('uuid'), uid('label', name, x, y)]])


def power(net, x, y, rot=0):
    pwr_count[0] += 1
    ref = '#PWR%03d' % pwr_count[0]
    place_symbol(POWER_NETS[net], ref, net, x, y, rot=rot, in_bom=False, on_board=False)


def pwr_flag(x, y, rot=0):
    pwr_count[0] += 1
    ref = '#FLG%03d' % pwr_count[0]
    place_symbol('power:PWR_FLAG', ref, 'PWR_FLAG', x, y, rot=rot, in_bom=False, on_board=False)


def no_connect(x, y):
    items.append([Sym('no_connect'), [Sym('at'), r2(x), r2(y)], [Sym('uuid'), uid('nc', x, y)]])


def text(s, x, y, size=2.0):
    items.append([Sym('text'), s, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), r2(x), r2(y), 0],
                  effects(size=size, justify='left bottom'), [Sym('uuid'), uid('text', s)]])


def connect_pin(net, px, py, d):
    """Odcinek od końca pinu na zewnątrz i etykieta / symbol zasilania."""
    ex, ey = px + d[0] * STUB, py + d[1] * STUB
    wire(px, py, ex, ey)
    mark_wire(net, px, py, ex, ey)
    if net in POWER_NETS:
        # obrót tak, by symbol „wychodził” dalej w kierunku d (GND domyślnie w dół, reszta w górę)
        if net == 'GND':
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        else:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        power(net, ex, ey, rot)
        mark(net, ex, ey)
    else:
        label(net, ex, ey, d)
        mark(net, ex, ey)


OUTWARD = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}


def main():
    for p in design.parts:
        b = p['bom']
        fields = {}
        if b.get('mfr') and b['mfr'] != '—':
            fields['Manufacturer'] = b['mfr']
            fields['MPN'] = b.get('mpn', '')
        if b.get('tme') and b['tme'] != '—':
            fields['TME'] = b['tme']
        if b.get('amazon'):
            fields['Amazon'] = b['amazon']
        if p['desc']:
            fields['Opis'] = p['desc']
        x, y = SCH_POS[p['ref']]
        ls = place_symbol(p['lib'], p['ref'], p['value'], x, y, footprint=p['fp'], fields=fields,
                          dnp=p['dnp'], key=p['ref'])
        # piny zgrupowane po położeniu (piny zasilania bywają nałożone na siebie)
        bypos = {}
        for pin in sym_pins(ls):
            bypos.setdefault((pin['x'], pin['y'], pin['ang']), []).append(pin)
        for (sx, sy, ang), group in bypos.items():
            nets = {p['pins'].get(g['num'], 'MISSING') for g in group}
            if len(nets) != 1:
                raise SystemExit('%s: piny %s w jednym miejscu mają różne sieci %s'
                                 % (p['ref'], [g['num'] for g in group], nets))
            net = nets.pop()
            if net == 'MISSING':
                raise SystemExit('%s: brak sieci dla pinu %s' % (p['ref'], group[0]['num']))
            px, py = x + sx, y - sy
            if net is None:
                no_connect(px, py)
                mark('NC:%s.%s' % (p['ref'], group[0]['num']), px, py)
            else:
                connect_pin(net, px, py, OUTWARD[ang])
    # flagi zasilania: sieci zasilane wyłącznie przez piny pasywne
    for i, net in enumerate(['VBUS', '+5V', 'GND']):
        fx, fy = 27.94 + i * 12.7, 25.4
        mark_wire(net, fx, fy, fx, fy + 5.08)
        wire(fx, fy, fx, fy + 5.08)
        if net == 'GND':
            pwr_flag(fx, fy, 0)
            power(net, fx, fy + 5.08, 0)
        else:
            power(net, fx, fy, 0)
            pwr_flag(fx, fy + 5.08, 180)
    for s, x, y in [
        ('USB-C, ochrona ESD, bezpiecznik, LDO 3,3 V', 22.86, 38.1),
        ('MCU STM32F072CBT6: odsprzęganie, kwarc 8 MHz (opcja)', 142.24, 81.28),
        ('Złącze OLED 2,42" I²C (SSD1309) i wybór zasilania modułu', 251.46, 33.02),
        ('Enkodery EC11 i suwak 45 mm', 340.36, 38.1),
        ('Klawisze Kailh Choc V2 (hotswap): bezpośrednio do MCU, podciąganie wewnętrzne', 22.86, 111.76),
        ('RESET / BOOT0 (od spodu) i SWD', 279.4, 93.98),
        ('Konwerter poziomu danych LED 3,3 → 5 V', 279.4, 134.62),
        ('LED WS2812B na spodzie płytki (łańcuch L1 → L12), 100 nF przy każdej', 22.86, 198.12),
        ('Otwory M3', 373.38, 142.24),
    ]:
        text(s, x, y)
    text('Flagi zasilania (ERC)', 22.86, 17.78, 1.5)

    sch = [Sym('kicad_sch'), [Sym('version'), 20260306], [Sym('generator'), 'eeschema'],
           [Sym('generator_version'), '10.0'], [Sym('uuid'), ROOT_UUID], [Sym('paper'), 'A3'],
           [Sym('title_block'), [Sym('title'), 'ChocPilot v2'], [Sym('date'), '2026-10-29'],
            [Sym('rev'), '2.0'], [Sym('comment'), 1, 'Makropad 2×4 Kailh Choc V2, OLED 2,42" I²C, 2× EC11, suwak, 12× WS2812B'],
            [Sym('comment'), 2, 'MCU STM32F072CBT6 (LQFP-48), USB-C, LDO TPS73633'],
            [Sym('comment'), 3, 'Wygenerowano: pcb/chocpilot-v2/tools/gen_sch.py (źródło: design.py)']],
           [Sym('lib_symbols')] + [lib_cache[k] for k in sorted(lib_cache)]]
    sch += items
    sch.append([Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]])
    sch.append([Sym('embedded_fonts'), Sym('no')])
    # lib_symbols trzeba znać przed zapisem – place_symbol wypełnił lib_cache
    sch[7] = [Sym('lib_symbols')] + [lib_cache[k] for k in sorted(lib_cache)]
    with open(OUT, 'w') as f:
        f.write(dump(sch) + '\n')
    print('zapisano', os.path.normpath(OUT), len(items), 'elementów')


if __name__ == '__main__':
    main()
