"""Evaluate the AST/API-leaf tokenizer: (1) category rules on dataset + real code, (2) style from structure tokens, (3) dump vectors for matrix.jl."""
import ast, json, sys, textwrap, collections, numpy as np
sys.path.insert(0, '.')
from asttok import Unit, struct_tokens, category
from stylelib import strip_docs
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import TruncatedSVD
D = json.load(open('texts.json')); items = D['items']
ds = [x for x in items if x['kind'] == 'dataset']; rl = [x for x in items if x['kind'] == 'real']
# ---- dataset
tok_ds, cat_ds = [], []
for x in ds:
    u = Unit(x['raw']); names = [n for n in u.defs]
    top = [d for d in u.tree.body]  # tokens over whole snippet
    toks = []
    for node in u.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)): toks += struct_tokens(u, node)
    tok_ds.append(toks); cat_ds.append(category(u, names)[0])
top_ok = np.array([c[0] == x['top'] for c, x in zip(cat_ds, ds)])
sub_ok = np.array([(c[1] == x['sub']) or (x['top'] == 'compute' and c[0] == 'compute') or (x['top'] == 'glue' and c[0] == 'glue') for c, x in zip(cat_ds, ds)])
print('DATASET top acc %.2f | sub acc (io: fs/net exact; compute/glue: top only) %.2f' % (top_ok.mean(), sub_ok.mean()))
for t in ['compute', 'io', 'glue']:
    m = np.array([x['top'] == t for x in ds]); print('  ', t, 'top acc %.2f' % top_ok[m].mean())
for st in 'POFDG':
    m = np.array([x['style'] == st for x in ds]); print('   style', st, 'top acc %.2f' % top_ok[m].mean())
bad = collections.Counter((x['intent'], x['style'], c[0]) for c, x, ok in zip(cat_ds, ds, top_ok) if not ok)
print('  misses:', sorted(bad))
# ---- real code
import statistics, collections as coll, argparse, shutil, glob, filecmp, urllib.request as urq, ftplib, smtplib
import numpy.lib._function_base_impl as npf, networkx.algorithms.shortest_paths.generic as nxg, networkx.algorithms.shortest_paths.unweighted as nxu, networkx.algorithms.traversal.breadth_first_search as nxb
MODS = {'statistics': [statistics], 'collections': [coll], 'argparse': [argparse], 'numpy_lib': [npf], 'networkx_paths': [nxg, nxu, nxb],
        'stdlib_fs': [shutil, glob, filecmp], 'stdlib_net': [urq, ftplib, smtplib]}
byraw = {}
for corp, mods in MODS.items():
    for m in mods:
        src = open(m.__file__).read(); u = Unit(src)
        for n in ast.walk(u.tree):
            if isinstance(n, ast.FunctionDef):
                seg = ast.get_source_segment(src, n)
                try: raw = strip_docs(textwrap.dedent(seg))
                except SyntaxError: continue
                byraw.setdefault((corp, raw), (u, n))
tok_rl, cat_rl, miss = [], [], 0
for x in rl:
    k = byraw.get((x['corpus'], x['raw']))
    if k is None: miss += 1; tok_rl.append([]); cat_rl.append((None, None)); continue
    u, n = k; tok_rl.append(struct_tokens(u, n)); cat_rl.append(category(u, [n.name])[0])
print('real functions not matched to module source:', miss)
print('REAL CODE (expected labels from module): top acc / sub acc / predicted-top share')
for c in ['statistics', 'numpy_lib', 'networkx_paths', 'collections', 'argparse', 'stdlib_fs', 'stdlib_net']:
    idx = [i for i, x in enumerate(rl) if x['corpus'] == c]; e = (rl[idx[0]]['top'], rl[idx[0]]['sub'])
    share = collections.Counter(cat_rl[i][0] for i in idx); n = len(idx)
    ta = np.mean([cat_rl[i][0] == e[0] for i in idx]) if e[0] else float('nan'); sa = np.mean([cat_rl[i][1] == e[1] for i in idx]) if e[1] and e[0] == 'io' else float('nan')
    print('  %-15s n=%2d top %.2f sub %.2f  %s' % (c, n, ta, sa, {k: round(v / n, 2) for k, v in share.items()}))
# ---- style from structure tokens (LOIO)
intent = np.array([x['intent'] for x in ds]); style = np.array([x['style'] for x in ds]); I = sorted(set(intent))
def loio(X, mask_fn=None):
    acc = []
    for i in I:
        tr = intent != i; clf = LogisticRegression(max_iter=4000, C=10).fit(X[tr], style[tr]); acc.append((clf.predict(X[~tr]) == style[~tr]).mean())
    return round(float(np.mean(acc)), 2)
def ngrams(toks, n=2): return toks + ['|'.join(toks[i:i + n]) for i in range(len(toks) - n + 1)]
full = [' '.join(t.replace(' ', '_') for t in ngrams(ts)) for ts in tok_ds]
vec = TfidfVectorizer(token_pattern=r'\S+', lowercase=False, min_df=2, sublinear_tf=True); X = vec.fit_transform(full).toarray()
noapi = [' '.join(t for t in ngrams([t for t in ts if not t.startswith(('LEAF:', 'CALL:api', 'CALL:lib'))])) for ts in tok_ds]
X2 = TfidfVectorizer(token_pattern=r'\S+', lowercase=False, min_df=2, sublinear_tf=True).fit_transform(noapi).toarray()
print('STYLE LOIO acc (chance .20): structure+API tokens %.2f | structure only (no API/lib tokens) %.2f   [baselines: keyword tf-idf .87, embeddings .54-.77]' % (loio(X), loio(X2)))
# category from the same tokens' API leaves is by rule; also check kNN-style category with tf-idf (LOIO)
top = np.array([x['top'] for x in ds])
acc = []
for i in I:
    tr = intent != i; clf = LogisticRegression(max_iter=4000, C=10).fit(X[tr], top[tr]); acc.append((clf.predict(X[~tr]) == top[~tr]).mean())
print('top-category LOIO from tf-idf of tokens (learned, not rule) %.2f' % np.mean(acc))
# ---- dump 128-d vectors as a pseudo-model for matrix.jl (dataset+real share one vocabulary)
allt = [' '.join(t.replace(' ', '_') for t in ngrams(ts)) for ts in tok_ds + tok_rl]
vec2 = TfidfVectorizer(token_pattern=r'\S+', lowercase=False, min_df=2, sublinear_tf=True); M = vec2.fit_transform(allt)
Z = TruncatedSVD(64, random_state=0).fit_transform(M); Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
for v in ['raw', 'hashed']:
    np.savetxt(f'jl/asttok_{v}_ds.tsv', Z[:len(ds)], delimiter='\t', fmt='%.6g'); np.savetxt(f'jl/asttok_{v}_real.tsv', Z[len(ds):], delimiter='\t', fmt='%.6g')
json.dump(dict(cat_ds=[list(c) for c in cat_ds], cat_rl=[list(c) for c in cat_rl]), open('out/asttok_categories.json', 'w'))
print('wrote jl/asttok_*')
