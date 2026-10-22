"""Category with the GENERATED preset (build_preset.py) instead of the hand-written PLATFORM table of asttok.py."""
import ast, json, sys, textwrap, collections, numpy as np
sys.path.insert(0, '.')
import asttok
from asttok import Unit, category
from build_preset import Preset, IO_TAGS, dotted
from stylelib import strip_docs
P = Preset()
MODE = {'m': 'plain'}
TAG2CAT = {'net': ('io', 'network'), 'proc': ('io', 'process'), 'fs': ('io', 'filesystem')}
PRIO = ['net', 'proc', 'fs']
def io_tag(tags):
    for t in PRIO:
        if t in tags: return t
    return None

class PresetUnit(Unit):
    def classify_call(self, c):
        f = c.func
        if isinstance(f, ast.Name):
            if f.id in self.defs: return ('local', f.id)
            full = self.alias.get(f.id, f.id if f.id == 'open' else None)
            if f.id == 'open' and f.id not in self.alias: full = 'builtins.open'
            if full:
                r = P.resolve_full(full); tags = self._tags(r, full)
                t = io_tag(tags)
                if t: return ('api', full, TAG2CAT[t])
                return ('lib', full)
            return ('builtin', f.id) if f.id in asttok.PURE_BUILTINS else ('opaque', f.id)
        if isinstance(f, ast.Attribute):
            d = dotted(f)
            if d:
                root = d.split('.')[0]
                if root in self.alias:
                    full = '.'.join([self.alias[root]] + d.split('.')[1:]); r = P.resolve_full(full); tags = self._tags(r, full)
                    t = io_tag(tags)
                    if t: return ('api', full, TAG2CAT[t])
                    return ('lib', full)
                if root == 'self' and f.attr in self.defs: return ('local', f.attr)
                if root == 'self': return ('opaque', d)
            if isinstance(f.value, ast.Call):
                dd = dotted(f.value.func)
                if dd and dd.split('.')[0] in self.alias:
                    full = '.'.join([self.alias[dd.split('.')[0]]] + dd.split('.')[1:] + [f.attr]); tags = self._tags(P.resolve_full(full), full); t = io_tag(tags)
                    if t: return ('api', full, TAG2CAT[t])
            if f.attr in self.defs and f.attr not in ('read', 'write', 'close', 'flush'): return ('local', f.attr)
            mt = P.method_tag(f.attr)      # derived from the stdlib: only if its definitions agree
            if mt in IO_TAGS: return ('api', '.' + f.attr, TAG2CAT[mt])
            return ('method', f.attr)
        return ('opaque', '?')
    def _tags(self, r, full=None):
        tags = set() if not r else ({r[1]} if r[0] == 'tag' else set(P.tags.get(r[1], ())))
        if not (tags & IO_TAGS) and MODE['m'] != 'plain':   # nothing reached: fall back to the module's derived prior
            name = (r[1] if r and r[0] == 'func' else full or '')
            parts = name.split('.')
            for i in range(len(parts), 0, -1):
                if '.'.join(parts[:i]) in P.mods:
                    mn = '.'.join(parts[:i]); mp = P.module_prior(mn) or (P.import_prior(mn) if MODE['m'] == 'import' else None)
                    if mp: tags = tags | {mp}
                    break
        return tags

D = json.load(open('texts.json')); items = D['items']
ds = [x for x in items if x['kind'] == 'dataset']; rl = [x for x in items if x['kind'] == 'real']

def run_ds(UnitCls):
    out = []
    for x in ds:
        u = UnitCls(x['raw']); out.append(category(u, list(u.defs))[0])
    return out
res = {}
for name, cls, mode in [('hand table (asttok.py)', Unit, 'plain'), ('preset plain', PresetUnit, 'plain'), ('preset + module prior', PresetUnit, 'module'), ('preset + module + import prior', PresetUnit, 'import')]:
    MODE['m'] = mode; cat = run_ds(cls)
    top = np.array([c[0] == x['top'] for c, x in zip(cat, ds)])
    sub = np.array([(c[1] == x['sub']) for c, x in zip(cat, ds) if x['top'] == 'io'])
    res[name] = dict(top=top.mean(), io=np.mean([t for t, x in zip(top, ds) if x['top'] == 'io']), compute=np.mean([t for t, x in zip(top, ds) if x['top'] == 'compute']),
                     glue=np.mean([t for t, x in zip(top, ds) if x['top'] == 'glue']), io_sub=sub.mean())
    print('SNIPPETS', name, {k: round(float(v), 2) for k, v in res[name].items()})

import statistics, collections as coll, argparse, shutil, glob, filecmp, urllib.request as urq, ftplib, smtplib
import numpy.lib._function_base_impl as npf, networkx.algorithms.shortest_paths.generic as nxg, networkx.algorithms.shortest_paths.unweighted as nxu, networkx.algorithms.traversal.breadth_first_search as nxb
MODS = {'statistics': [statistics], 'collections': [coll], 'argparse': [argparse], 'numpy_lib': [npf], 'networkx_paths': [nxg, nxu, nxb],
        'stdlib_fs': [shutil, glob, filecmp], 'stdlib_net': [urq, ftplib, smtplib]}
def build_units(mode):
    MODE['m'] = mode; out = {}
    for corp, mods in MODS.items():
        for m in mods:
            src = open(m.__file__).read()
            for UnitCls, tag in ((Unit, 'hand'), (PresetUnit, 'preset')):
                if tag == 'hand' and mode != 'plain': continue
                u = UnitCls(src)
                for n in ast.walk(u.tree):
                    if isinstance(n, ast.FunctionDef):
                        try: raw = strip_docs(textwrap.dedent(ast.get_source_segment(src, n)))
                        except SyntaxError: continue
                        out.setdefault((corp, raw, tag), (u, n))
    return out
UNITS = {mode: build_units(mode) for mode in ('plain', 'module', 'import')}
print('REAL top-category accuracy against module-name expectation (hand table | generated preset); sub accuracy for IO')
for c in ['statistics', 'numpy_lib', 'networkx_paths', 'collections', 'argparse', 'stdlib_fs', 'stdlib_net']:
    idx = [x for x in rl if x['corpus'] == c]; e = (idx[0]['top'], idx[0]['sub']); row = []
    for tag, mode in (('hand', 'plain'), ('preset', 'plain'), ('preset', 'module'), ('preset', 'import')):
        MODE['m'] = mode; cats = []; BY = UNITS['plain' if tag == 'hand' else mode]
        for x in idx:
            u, n = BY[(c, x['raw'], tag)]; cats.append(category(u, [n.name])[0])
        share = collections.Counter(k[0] for k in cats)
        ta = np.mean([k[0] == e[0] for k in cats]) if e[0] else float('nan'); sa = np.mean([k[1] == e[1] for k in cats]) if e[0] == 'io' else float('nan')
        row.append('%.2f/%.2f' % (ta, sa) if e[0] else 'io share %.2f' % (share.get('io', 0) / len(idx)))
    print('  %-15s hand %s | preset %s | +module %s | +module+import %s' % (c, *row))
