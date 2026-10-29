"""BOM z design.py: bom/chocpilot-v2-bom.csv i bom/BOM.md.

Pozycje o tym samym numerze producenta są łączone. Klawisze S1–S8 rozbijane są na gniazdo
hotswap i przełącznik; na końcu części spoza płytki (keycapy, gałki, moduł OLED, śruby).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), '..', 'bom')

# Symbole TME sprawdzone w katalogu tme.eu 2026-10-29 (istnieją, „Available in stock” > 0
# dla co najmniej jednego wariantu). Pozostałe numery TME podano wg schematu nazewnictwa TME
# – do potwierdzenia przy zamówieniu (to typowe elementy 0805, łatwe do zastąpienia).
TME_CHECKED = {
    'STM32F072CBT6', 'TPS73633DBVR', 'USBLC6-2SC6', 'USB4105-GF-A', 'SN74AHCT1G125DBVR',
    'WS2812B-V5', 'EC11E15244G1', 'PTA45432015DPA10-0', 'PTS645SM43SMTR92', 'MF-NSMF050-2',
    'ABM3-8.000MHZ-D2Y', 'ZL262-4SG', 'RC0805FR-075K1', 'CL21B104KBCNNNC', 'CL21A106KAYNNNE',
    'CL21A475KAQNNNE',
}

PKG_KIND = {'Device:R': 'SMD', 'Device:C': 'SMD'}

EXTRA = [
    # (oznaczenia, ilość, opis, obudowa, producent, nr, tme, amazon, montaż, uwagi)
    ('S1–S8', 8, 'Gniazdo hotswap Kailh Choc (V1/V2)', 'SMD', 'Kailh', 'CPG135001S30', '—',
     'amazon.de B0CJQHMYDW (50 szt., „Low Profile Socket … Kailh 1350”)', 'SMD (spód)',
     'brak w TME; lutowane od spodu na pady 1 i 2'),
    ('S1–S8', 8, 'Przełącznik Kailh Choc V2 (low profile, trzpień MX)', 'THT (wciskany)', 'Kailh',
     'CPG1353 (Choc V2)', '—', 'amazon.de B0CMZWF635 (Kailh Choc V2 Brown) lub inny Choc V2',
     'wciskany w gniazdo', 'brak w TME; pasują też Choc V1 (CPG1350)'),
    ('—', 8, 'Keycap 1u w profilu MX (Choc V2 ma trzpień MX)', '—', '—', '—', '—',
     'keycaps MX 1u (np. low profile)', '—', 'raster 19,05 mm'),
    ('ENC1, ENC2', 2, 'Gałka do enkodera, oś 6 mm D, Ø ≤ 18 mm', '—', '—', '—', '—',
     'potentiometer knob 6 mm D shaft', '—', 'oś D 6 mm'),
    ('RV1', 1, 'Nakładka na dźwignię suwaka Bourns PTA', '—', '—', '—', '—',
     'slide potentiometer knob cap', '—', 'wąska (≤ 8 mm) – patrz DESIGN_NOTES'),
    ('J2', 1, 'Moduł OLED 2,42" SSD1309 128×64 I²C, 4 piny', '70,10 × 48,10 mm', 'ShengYang', '—', '—',
     '2.42 inch OLED SSD1309 I2C 4 pin', 'na gniazdo J2', 'jak w ChocPilot v1'),
    ('J2', 1, 'Listwa kołkowa 1×4 2,54 mm do modułu (jeśli moduł jej nie ma)', 'THT', 'Connfly',
     'DS1021-1*4SF11', 'ZL201-04G', 'pin header 2.54 mm', 'THT', 'do potwierdzenia w TME'),
    ('H1–H4', 4, 'Śruba M3 × 6 + tuleja dystansowa / wkładka do obudowy', '—', '—', '—', '—',
     'M3 screws assortment', '—', 'zależnie od obudowy'),
]


def rows():
    groups = {}
    order = []
    for p in design.parts:
        if p['ref'].startswith('S') and p['ref'][1:].isdigit():
            continue                       # klawisze: osobne pozycje w EXTRA
        b = p['bom']
        if p['ref'].startswith('H') or p['ref'].startswith('JP'):
            continue                       # otwory i zworki lutowane: nie są częściami
        key = (b.get('mpn'), p['value'], p['fp'])
        if key not in groups:
            groups[key] = dict(refs=[], part=p)
            order.append(key)
        groups[key]['refs'].append(p['ref'])
    out = []
    for key in order:
        g = groups[key]
        p = g['part']
        b = p['bom']
        refs = sorted(g['refs'], key=lambda r: (r.rstrip('0123456789'), int(''.join(c for c in r if c.isdigit()) or 0)))
        tme = b.get('tme', '—')
        notes = []
        if p['dnp']:
            notes.append('DNP – opcjonalne')
        if tme not in ('—', '') and tme not in TME_CHECKED:
            notes.append('nr TME do potwierdzenia')
        if p['ref'] == 'RV1':
            notes.append('TME ma tylko charakterystykę log. (A) – firmware linearyzuje; liniowa B103 – Amazon')
        if p['ref'] == 'Y1':
            notes.append('opcjonalny – USB działa bez kwarcu')
        thtfp = any(k in p['fp'] for k in ('THT', 'PinHeader', 'PinSocket', 'Rotary_Encoder'))
        kind = 'THT' if thtfp else 'SMD'
        if p['pcb'][3] == 'B':
            kind += ' (spód)'
        out.append([', '.join(compress(refs)), len(refs), describe(p), b.get('pkg', ''), p['fp'],
                    b.get('mfr', ''), b.get('mpn', ''), tme, b.get('amazon', ''), kind, '; '.join(notes)])
    for e in EXTRA:
        out.append([e[0], e[1], e[2], e[3], '', e[4], e[5], e[6], e[7], e[8], e[9]])
    return out


def describe(p):
    if p['lib'] == 'Device:R':
        return 'Rezystor %sΩ 1%% 0805' % p['value']
    if p['lib'] == 'Device:C':
        diel = 'C0G' if 'p' in p['value'] else ('X5R' if p['value'] in ('4.7uF', '10uF') else 'X7R')
        return 'Kondensator %s %s 0805' % (p['value'].replace('u', 'µ'), diel)
    return (p['desc'][:1].upper() + p['desc'][1:]) if p['desc'] else p['value']


def compress(refs):
    """C19, C20, …, C30 → C19–C30."""
    out = []
    run = []

    def flush():
        if len(run) > 2:
            out.append('%s–%s' % (run[0], run[-1]))
        else:
            out.extend(run)

    for r in refs:
        pre = r.rstrip('0123456789')
        n = int(r[len(pre):])
        if run and run[-1].rstrip('0123456789') == pre and int(run[-1][len(pre):]) == n - 1:
            run.append(r)
        else:
            flush()
            run = [r]
    flush()
    return out


HEAD = ['Oznaczenia', 'Ilość', 'Opis', 'Obudowa', 'Footprint KiCad', 'Producent', 'Nr producenta',
        'TME', 'Amazon (alternatywa)', 'Montaż', 'Uwagi']


def main():
    os.makedirs(OUT, exist_ok=True)
    data = rows()
    with open(os.path.join(OUT, 'chocpilot-v2-bom.csv'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')     # LF jak reszta repozytorium
        w.writerow(['Poz.'] + HEAD)
        for i, r in enumerate(data, 1):
            w.writerow([i] + r)
    md = ['# ChocPilot v2 – BOM', '',
          'Wygenerowano z `tools/design.py` (`python3 tools/gen_bom.py`). Ten sam plik jako CSV: '
          '[chocpilot-v2-bom.csv](chocpilot-v2-bom.csv).', '',
          'Numery TME sprawdzone w katalogu tme.eu 29.10.2026 (pozycja istnieje i co najmniej jeden '
          'wariant był na stanie). „Do potwierdzenia” = numer wg nazewnictwa TME, nie sprawdzony – '
          'to zwykłe elementy 0805, każdy odpowiednik o tej samej wartości i dielektryku pasuje.', '',
          '| Poz. | ' + ' | '.join(h for h in HEAD if h != 'Footprint KiCad') + ' |',
          '|' + '---|' * (len(HEAD)) ]
    for i, r in enumerate(data, 1):
        cells = [str(i)] + [str(c) for j, c in enumerate(r) if HEAD[j] != 'Footprint KiCad']
        md.append('| ' + ' | '.join(c.replace('|', '/') for c in cells) + ' |')
    md += ['', '## Footprinty', '', '| Oznaczenia | Footprint KiCad |', '|---|---|']
    for r in data:
        if r[4]:
            md.append('| %s | `%s` |' % (r[0], r[4]))
    n_smd = sum(r[1] for r in data if r[9].startswith('SMD') and r[4])
    n_tht = sum(r[1] for r in data if r[9].startswith('THT') and r[4])
    md += ['', 'Elementów lutowanych na płytce: %d SMD, %d THT (bez gniazd hotswap: +8 SMD).' % (n_smd, n_tht), '']
    open(os.path.join(OUT, 'BOM.md'), 'w').write('\n'.join(md))
    print('zapisano', os.path.normpath(OUT), len(data), 'pozycji')


if __name__ == '__main__':
    main()
