import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, find, find1
S = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/'
for spec in sys.argv[1:]:
    lib, name = spec.split(':')
    root = parse(open(S + lib + '.kicad_sym').read())
    syms = {s[1]: s for s in find(root, 'symbol')}
    s = syms[name]
    ext = find1(s, 'extends')
    chain = [name]
    while ext:
        s = syms[ext[1]]; chain.append(ext[1]); ext = find1(s, 'extends')
    pins = []
    for u in find(s, 'symbol'):
        for p in find(u, 'pin'):
            at = find1(p, 'at'); nm = find1(p, 'name')[1]; num = find1(p, 'number')[1]
            pins.append((num, nm, p[1], at[1], at[2], at[3] if len(at) > 3 else 0, u[1]))
    print('==', spec, '->', chain, len(pins), 'pins')
    for x in sorted(pins, key=lambda x: (x[6], x[0])):
        print('  ', x)
