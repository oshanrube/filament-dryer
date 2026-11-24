"""Minimal S-expression reader/writer for KiCad files."""
import re

TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """An unquoted atom."""


def parse(text):
    stack, cur = [], []
    for m in TOKEN.finditer(text):
        lp, rp, s, a = m.groups()
        if lp:
            stack.append(cur); cur = []
        elif rp:
            done = cur; cur = stack.pop(); cur.append(done)
        elif s is not None:
            cur.append(s[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        elif a is not None:
            cur.append(Sym(a))
    return cur


def dump(x, indent=0):
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return "(" + " ".join(dump(e) for e in x) + ")"
        out = "(" + dump(x[0])
        for e in x[1:]:
            out += ("\n" + "  " * (indent + 1) + dump(e, indent + 1)) if isinstance(e, list) else (" " + dump(e))
        return out + ")"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, (int, float)):
        return f"{x:g}" if isinstance(x, float) else str(x)
    return '"' + str(x).replace("\\", "\\\\").replace('"', '\\"') + '"'


def find(lst, head):
    return [e for e in lst if isinstance(e, list) and e and e[0] == head]


def first(lst, head):
    r = find(lst, head)
    return r[0] if r else None
