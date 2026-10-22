import sys, random, ast, textwrap, json; sys.path.insert(0,'.')
from build_preset2 import Preset2, IO_TAGS
from asttok import Unit, category
from stylelib import strip_docs
import shutil, glob, filecmp, urllib.request as urq, ftplib, smtplib
P = Preset2(escape=True); random.seed(1)
D = json.load(open('texts.json')); rl = [x for x in D['items'] if x['kind'] == 'real' and x['corpus'] in ('stdlib_fs', 'stdlib_net')]
rows = {}
for m in (shutil, glob, filecmp, urq, ftplib, smtplib):
    src = open(m.__file__).read(); u = Unit(src); mm = P.mods[m.__name__]
    for key, node in mm.funcs.items():
        raw = strip_docs(textwrap.dedent(ast.get_source_segment(src, node)))
        rows.setdefault(raw, (key, node, u))
A, B = [], []
for x in rl:
    if x['raw'] not in rows: continue
    key, node, u = rows[x['raw']]
    hand = category(u, [node.name])[0][0] == 'io'; pre = bool(P.tags.get(key, set()) & IO_TAGS)
    calls = sorted({ast.unparse(c.func) for c in ast.walk(node) if isinstance(c, ast.Call)})[:9]
    (A if hand and not pre else B if pre and not hand else []).append((key.split('.', 1)[1], calls, sorted(P.tags.get(key, set()))))
print('hand=io, preset=not:', len(A)); [print('  ', a[0], a[1]) for a in random.sample(A, min(14, len(A)))]
print('preset=io, hand=not:', len(B)); [print('  ', b[0], b[1], b[2]) for b in random.sample(B, min(10, len(B)))]
