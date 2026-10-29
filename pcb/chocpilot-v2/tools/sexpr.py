"""Minimalny parser/zapis S-wyrażeń KiCad (pliki .kicad_sym / .kicad_sch)."""
import re

_TOKEN = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


class Sym(str):
    """Symbol (atom bez cudzysłowu), odróżniany od napisu w cudzysłowie."""


def parse(text):
    pos = 0
    stack = [[]]
    for m in _TOKEN.finditer(text):
        tok = m.group(1)
        if tok == '(':
            stack.append([])
        elif tok == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif tok.startswith('"'):
            stack[-1].append(tok[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            stack[-1].append(Sym(tok))
    return stack[0][0]


def _atom(x):
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, str):
        return '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, float):
        s = ('%.4f' % x).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(x)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(_atom(c) for c in node) + ')'
    out = '(' + ' '.join(_atom(c) for c in node if not isinstance(c, list))
    for c in node:
        if isinstance(c, list):
            out += '\n' + '\t' * (indent + 1) + dump(c, indent + 1)
    return out + '\n' + '\t' * indent + ')'


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
