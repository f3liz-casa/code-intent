"""Export (Intent features -> style features) tables for the Julia trainer.

usage: python3 -I export_intent_style.py <extract dir with units.jsonl> <analyze dir with unit_styles.jsonl> <out dir> [--lang typescript]
Order of unit_styles.jsonl equals units.jsonl restricted to loc >= 3 (analyze.py), checked by (file, line, name).

Intent side (X): layer one-hot, effect category one-hot, name verb (top 40 + other), reachable leaves multi-hot, language one-hot.
Style side  (Y): 17 structure features (no names, no leaves), standardized; mean/sd are saved so scores can be un-standardized.
"""
import json, math, sys, collections, hashlib

src, ana, out = sys.argv[1:4]
lang = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'typescript'
U = [json.loads(l) for l in open(f'{src}/units.jsonl')]
U = [u for u in U if u['loc'] >= 3]
S = [json.loads(l) for l in open(f'{ana}/unit_styles.jsonl')]
assert len(U) == len(S), (len(U), len(S))
for u, s in zip(U, S):
    assert (u['file'], u['line'], u['name']) == (s['file'], s['line'], s['name'])

FN = ['loops', 'chain', 'mutate', 'let_share', 'awaits', 'thens', 'uses_this', 'in_class', 'switch', 'ternary', 'try', 'throw', 'depth', 'loc', 'cyc', 'optional', 'nonnull']
def feats(u):
    ls = u['lets'] + u['consts']
    return [math.log1p(u['loops']), math.log1p(u['chain']), math.log1p(u['mutate']), u['lets'] / ls if ls else 0.0, math.log1p(u['awaits']), math.log1p(u['thens']),
            float(u['thisUse'] > 0), float(u['cls'] is not None), math.log1p(u['sw']), math.log1p(u['tern']), math.log1p(u['tries']), math.log1p(u['throws']),
            math.log1p(u['maxDepth']), math.log1p(u['loc']), math.log1p(u['cyc']), math.log1p(u['opt']), math.log1p(u['nonNull'])]
def verb(name):
    w = ''.join(c if c.islower() or not c.isalpha() else ' ' + c.lower() for c in (name or '')).split()
    return w[0] if w else ''

layers = sorted({s['layer'] for s in S}); cats = sorted({s['cat'] for s in S})
leaves = sorted({l for s in S for l in s['leaves']})
vc = collections.Counter(verb(s['name']) for s in S)
verbs = [v for v, _ in vc.most_common(40) if v] + ['<other>']
cols = [f'layer={l}' for l in layers] + [f'cat={c}' for c in cats] + [f'verb={v}' for v in verbs] + [f'leaf={l}' for l in leaves] + [f'lang={lang}']
ix = {c: i for i, c in enumerate(cols)}
X = []; Y = []
for u, s in zip(U, S):
    x = [0] * len(cols)
    x[ix[f"layer={s['layer']}"]] = 1; x[ix[f"cat={s['cat']}"]] = 1
    v = verb(s['name']); x[ix[f'verb={v}' if f'verb={v}' in ix else 'verb=<other>']] = 1
    for l in s['leaves']: x[ix[f'leaf={l}']] = 1
    x[ix[f'lang={lang}']] = 1
    X.append(x); Y.append(feats(u))
n, d = len(Y), len(FN)
mu = [sum(r[j] for r in Y) / n for j in range(d)]; sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in Y) / n) + 1e-9 for j in range(d)]
with open(f'{out}/intent_X.tsv', 'w') as f:
    for r in X: f.write('\t'.join(map(str, r)) + '\n')
with open(f'{out}/style_Y.tsv', 'w') as f:
    for r in Y: f.write('\t'.join(f'{(r[j] - mu[j]) / sd[j]:.6f}' for j in range(d)) + '\n')
with open(f'{out}/style_cols.tsv', 'w') as f:
    for j in range(d): f.write(f'{FN[j]}\t{mu[j]:.6f}\t{sd[j]:.6f}\n')
with open(f'{out}/intent_cols.txt', 'w') as f: f.write('\n'.join(cols) + '\n')
with open(f'{out}/unit_meta.tsv', 'w') as f:
    for s in S:
        f.write('\t'.join([s['file'], str(s['line']), s['cls'] or '', s['name'] or '', s['layer'], s['cat'], lang, str(int(hashlib.md5(s['file'].encode()).hexdigest(), 16) % 5)]) + '\n')
print(f'{n} units, {len(cols)} intent features, {d} style features, folds by file hash')
