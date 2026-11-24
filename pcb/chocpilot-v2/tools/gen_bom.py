"""BOM z design.py: bom/chocpilot-v0-bom.csv i bom/BOM.md.

Pozycje o tym samym numerze producenta są łączone. Przełączniki S1–S8 (spoza TME) są osobną
pozycją w EXTRA; na końcu części spoza płytki (keycapy, gałki, ekran LCD, śruby).
Listwy kołkowe (J2, J3) są poza BOM – z własnego zapasu.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), '..', 'bom')

# Symbole TME sprawdzone w katalogu tme.eu 2026-11-04: pozycja jest na stanie TME i nie ma
# oznaczenia „Hardly available product” / „till the stock lasts” (wyjątki w TME_NOTES).
TME_CHECKED = {
    'STM32F072CBT6', 'TPS73633DBVR', 'USBLC6-2SC6', 'USB4105-GF-A', 'SN74AHCT1G125DBVR',
    'WS2812B-V6', 'EC11E15244G1', 'RS45111A900F', 'PTS645SM43SMTR92', 'MF-NSMF050-2',
    'ABM3-8.000MHZ-D2Y', 'RC0805FR-075K1', 'RC0805FR-0710K', 'RC0805FR-07330R', '1N4148W-E3-08',
    'KAM21BR71H104KT', 'KGM21NR72A103KT', 'KAM21KR71E105KU', 'KGM21AR71C475KU',
    'C0805C106M8RACTU', '08055A270GAT2A', 'WSH-17344',
}
TME_NOTES = {}

PKG_KIND = {'Device:R': 'SMD', 'Device:C': 'SMD'}

EXTRA = [
    # (oznaczenia, ilość, opis, obudowa, producent, nr, tme, amazon, montaż, uwagi)
    ('S1–S8', 8, 'Przełącznik Kailh Choc V2 (low profile, trzpień MX)', 'THT', 'Kailh',
     'CPG1353 (Choc V2)', 'brak w TME', 'amazon.de B0CMZWF635 (Kailh Choc V2 Brown) lub inny Choc V2',
     'THT (lutowany od spodu)', 'brak w TME; pasują też Choc V1 (CPG1350)'),
    ('—', 8, 'Keycap 1u w profilu MX (Choc V2 ma trzpień MX)', '—', '—', '—', 'brak w TME',
     'keycaps MX 1u (np. low profile)', '—', 'raster 19,05 mm'),
    ('ENC1, ENC2', 2, 'Gałka do enkodera, oś 6 mm D, Ø ≤ 18 mm', '—', '—', '—', '—',
     'potentiometer knob 6 mm D shaft', '—', 'oś D 6 mm'),
    ('RV1', 1, 'Nakładka na dźwignię suwaka ALPS RS (dźwignia 4 × 1,2 mm)', '—', '—', '—', '—',
     'slide potentiometer knob cap 4 x 1.2 mm', '—', 'wąska (≤ 8 mm) – patrz DESIGN_NOTES'),
    ('J2', 1, 'Ekran LCD 2" IPS 240×320, ST7789V, SPI (Waveshare 2inch LCD Module, z kablem PH2.0)',
     '58 × 35 mm', 'Waveshare', '17344', 'WSH-17344', '', 'w obudowie, kabel PH2.0 → J2',
     'kabel 1:1 na J2 (VCC na pin 1); zasilanie 3,3 V – logika modułu = VCC'),
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
        if 'PinHeader' in p['fp']:
            continue                       # listwy kołkowe: z własnego zapasu, poza BOM
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
        if tme in TME_NOTES:
            notes.append(TME_NOTES[tme])
        if p['ref'] == 'Y1':
            notes.append('opcjonalny – USB działa bez kwarcu')
        thtfp = any(k in p['fp'] for k in ('THT', 'PinHeader', 'PinSocket', 'Rotary_Encoder', 'Potentiometer'))
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
        diel = 'C0G' if 'p' in p['value'] else 'X7R'
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
    with open(os.path.join(OUT, 'chocpilot-v0-bom.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')     # LF jak reszta repozytorium
        w.writerow(['Poz.'] + HEAD)
        for i, r in enumerate(data, 1):
            w.writerow([i] + r)
    md = ['# ChocPilot v0 – BOM', '',
          'Wygenerowano z `tools/design.py` (`python3 tools/gen_bom.py`). Ten sam plik jako CSV: '
          '[chocpilot-v0-bom.csv](chocpilot-v0-bom.csv).', '',
          'Wszystkie elementy lutowane na płytce poza przełącznikami Kailh są w TME – numery sprawdzone '
          'w katalogu tme.eu 04.11.2026: na stanie TME w potrzebnej ilości i bez oznaczenia „Hardly '
          'available product” / „till the stock lasts”. Ekran (Waveshare WSH-17344) też jest w TME. TME nie sprzedaje produktów Kailh – '
          'przełączniki Choc V2 trzeba kupić gdzie indziej (Amazon), podobnie keycapy, gałki i nakładkę suwaka. Listwy kołkowe J2 (ekran) i J3 '
          '(SWD) nie są ujęte – z własnego zapasu.', '',
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
    md += ['', 'Elementów lutowanych na płytce: %d SMD, %d THT (+8 przełączników Choc THT).' % (n_smd, n_tht), '']
    open(os.path.join(OUT, 'BOM.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md))
    print('zapisano', os.path.normpath(OUT), len(data), 'pozycji')


if __name__ == '__main__':
    main()
