"""Evaluate the instance-aware preset (build_preset2.py): independent check + category tests, with and without the escape rule."""
import ast, json, sys, textwrap, collections, importlib.util, numpy as np
sys.path.insert(0, '.')
from asttok import Unit, category
from build_preset import IO_TAGS
from build_preset2 import Preset2
from stylelib import strip_docs
PRIO = ['net', 'proc', 'fs']; TAG2SUB = {'net': 'network', 'proc': 'process', 'fs': 'filesystem'}
def io_cat(tags):
    for t in PRIO:
        if t in tags: return ('io', TAG2SUB[t])
    return None
def shape(src, names):
    u = Unit(src); u.reach = {k: set() for k in u.defs}; return category(u, names)[0]

exec(open('check_preset.py').read().split("ok_tag =")[0].split("P = Preset()")[1].replace("TRUTH", "TRUTH"), globals()) if False else None
src_truth = open('check_preset.py').read(); TRUTH = eval(src_truth.split("TRUTH = ")[1].split("\nok_tag")[0].split("#", 1)[0] if False else "{" + src_truth.split("TRUTH = {")[1].split("\n}\n")[0].replace("  # qualified name -> expected tag set (empty = pure computation)", "") + "\n}")
def truth_check(P):
    ok_tag = n_tag = ok_pure = n_pure = 0
    for q, exp in TRUTH.items():
        r = P.ref_full(q)
        got = set(P.tags.get(r[1] if r[0] == 'func' else P.ctor(r[1]) or '', ())) if r and r[0] in ('func', 'class') else ({r[1]} if r and r[0] == 'tag' else set())
        if exp: n_tag += 1; ok_tag += bool(exp & got)
        else: n_pure += 1; ok_pure += not (got & IO_TAGS)
    return ok_tag, n_tag, ok_pure, n_pure

D = json.load(open('texts.json')); items = D['items']; ds = [x for x in items if x['kind'] == 'dataset']; rl = [x for x in items if x['kind'] == 'real']
import statistics, collections as coll, argparse, shutil, glob, filecmp, urllib.request as urq, ftplib, smtplib
import numpy.lib._function_base_impl as npf, networkx.algorithms.shortest_paths.generic as nxg, networkx.algorithms.shortest_paths.unweighted as nxu, networkx.algorithms.traversal.breadth_first_search as nxb
MODS = {'statistics': [statistics], 'collections': [coll], 'argparse': [argparse], 'numpy_lib': [npf], 'networkx_paths': [nxg, nxu, nxb],
        'stdlib_fs': [shutil, glob, filecmp], 'stdlib_net': [urq, ftplib, smtplib]}
def run(escape):
    P = Preset2(escape=escape); out = {}
    out['truth'] = truth_check(P)
    # snippets
    res = collections.defaultdict(list); sub = []
    for i, x in enumerate(ds):
        m = P.add_module(f'snip{i}', x['raw']); tags = set().union(*[P.tags[k] for k in m.funcs]) if m.funcs else set()
        c = io_cat(tags) or shape(x['raw'], [n.name for n in ast.walk(ast.parse(x['raw'])) if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
        res[x['top']].append(c[0] == x['top'])
        if x['top'] == 'io': sub.append(c[1] == x['sub'])
    out['snip'] = {k: float(np.mean(v)) for k, v in res.items()}; out['snip_io_sub'] = float(np.mean(sub))
    # real
    for corp, mods in MODS.items():
        rows = [x for x in rl if x['corpus'] == corp]; table = {}
        for m in mods:
            src = open(m.__file__).read(); name = m.__name__
            if name not in P.mods: P.add_module(name, src)
            mm = P.mods[name]
            for key, node in mm.funcs.items():
                try: raw = strip_docs(textwrap.dedent(ast.get_source_segment(src, node)))
                except Exception: continue
                table.setdefault(raw, (key, node, src))
            for key, node in mm.funcs.items():              # nested functions inherit the tags of their enclosing function
                for sub_ in ast.walk(node):
                    if isinstance(sub_, ast.FunctionDef) and sub_ is not node:
                        try: raw = strip_docs(textwrap.dedent(ast.get_source_segment(src, sub_)))
                        except Exception: continue
                        table.setdefault(raw, (key, sub_, src))
        cats = []
        for x in rows:
            if x['raw'] not in table:                       # nested class methods are not in the graph: shape rule only
                cs = shape(x['raw'], [ast.parse(x['raw']).body[0].name]); cats.append((cs[0], cs[1])); continue
            key, node, src = table[x['raw']]
            c = io_cat(P.tags.get(key, set()))
            if c is None:
                # shape rule on the function alone
                c = shape(textwrap.dedent(ast.get_source_segment(src, node)), [node.name])
                c = (c[0], c[1]) if isinstance(c, tuple) else (c, None)
            cats.append(c)
        e = (rows[0]['top'], rows[0]['sub']); n = len(rows)
        out[corp] = dict(top=float(np.mean([c[0] == e[0] for c in cats])) if e[0] else None, sub=float(np.mean([c[1] == e[1] for c in cats])) if e[0] == 'io' else None,
                         io_share=sum(c[0] == 'io' for c in cats) / n)
    return out
R = {esc: run(esc) for esc in (False, True)}
for esc, o in R.items():
    print('ESCAPE', esc, 'independent check: expected-tag found %d/%d, pure ok %d/%d' % o['truth'])
    print('  snippets top by class', {k: round(v, 2) for k, v in o['snip'].items()}, 'io sub %.2f' % o['snip_io_sub'])
    for c in MODS: print('  %-15s' % c, {k: (round(v, 2) if v is not None else None) for k, v in o[c].items()})
json.dump({str(k): v for k, v in R.items()}, open('out/preset2_eval.json', 'w'), indent=1, default=float)
