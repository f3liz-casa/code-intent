"""Merge per-repository unit files from extract_corpus.py into the TSV tables the Julia trainers read
(same layout as pilot/julia/export_intent_style.py + export_tokens.py, so latent_intent_style.jl loads them unchanged).

usage: python3 export_corpus.py <dir with *.units.jsonl.gz> <out dir> [--min-df 20] [--max-vocab 6000]
unit_meta.tsv columns: file, line, class, name, layer (language:role), hand category ('n/a': none exists for this corpus), language,
fold (md5 of the repository modulo 5, so folds hold out whole repositories), repository."""
import glob, gzip, hashlib, json, math, re, sys, collections

src, out = sys.argv[1:3]
min_df = int(sys.argv[sys.argv.index('--min-df') + 1]) if '--min-df' in sys.argv else 20
max_vocab = int(sys.argv[sys.argv.index('--max-vocab') + 1]) if '--max-vocab' in sys.argv else 6000
FN = ['loops', 'chain', 'mutate', 'let_share', 'awaits', 'thens', 'uses_this', 'in_class', 'switch', 'ternary', 'try', 'throw', 'depth', 'loc', 'cyc', 'optional', 'nonnull']
WORD = re.compile(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+')

def feats(u):
    ls = u['lets'] + u['consts']
    return [math.log1p(u['loops']), math.log1p(u['chain']), math.log1p(u['mutate']), u['lets'] / ls if ls else 0.0, math.log1p(u['awaits']), math.log1p(u['thens']),
            float(u['thisUse'] > 0), float(u['cls'] is not None), math.log1p(u['sw']), math.log1p(u['tern']), math.log1p(u['tries']), math.log1p(u['throws']),
            math.log1p(u['maxDepth']), math.log1p(u['loc']), math.log1p(u['cyc']), math.log1p(u['opt']), math.log1p(u['nonNull'])]

def tokens(u):
    t = []
    for c in u['callees']:
        c = re.sub(r'^(this|self)(\.|->|::)', '', c).replace('?.', '.').replace('->', '.').replace('::', '.')
        parts = [p for p in c.split('.') if p]
        if not parts: continue
        if len(parts) == 1: t.append('f:' + parts[0])
        else: t += ['c:' + parts[0] + '.' + parts[-1], 'm:' + parts[-1]]
    return t + ['n:' + w.lower() for w in WORD.findall(u['name'] or '')]

U = []
for p in sorted(glob.glob(f'{src}/*.units.jsonl.gz')):
    for l in gzip.open(p, 'rt'):
        U.append(json.loads(l))
n = len(U); print(n, 'units from', len(glob.glob(f'{src}/*.units.jsonl.gz')), 'repositories')
Y = [feats(u) for u in U]; d = len(FN)
mu = [sum(r[j] for r in Y) / n for j in range(d)]; sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in Y) / n) + 1e-9 for j in range(d)]
T = [tokens(u) for u in U]
df = collections.Counter(w for ts in T for w in set(ts))
vocab = [w for w, c in df.most_common(max_vocab) if c >= min_df]; vi = {w: i + 1 for i, w in enumerate(vocab)}
with open(f'{out}/style_Y.tsv', 'w') as f:
    for r in Y: f.write('\t'.join(f'{(r[j] - mu[j]) / sd[j]:.5f}' for j in range(d)) + '\n')
with open(f'{out}/style_cols.tsv', 'w') as f:
    for j in range(d): f.write(f'{FN[j]}\t{mu[j]:.6f}\t{sd[j]:.6f}\n')
with open(f'{out}/tokens_sparse.tsv', 'w') as f:
    for i, ts in enumerate(T, 1):
        for w, c in collections.Counter(w for w in ts if w in vi).items(): f.write(f'{i}\t{vi[w]}\t{c}\n')
with open(f'{out}/tokens_vocab.txt', 'w') as f: f.write('\n'.join(vocab) + '\n')
with open(f'{out}/unit_meta.tsv', 'w') as f:
    for u in U:
        fold = int(hashlib.md5(u['repo'].encode()).hexdigest(), 16) % 5
        f.write('\t'.join([u['file'], str(u['line']), u['cls'] or '', re.sub(r'\s+', '_', u['name']), u['layer'], 'n/a', u['lang'], str(fold), u['repo']]) + '\n')
print(len(vocab), 'tokens;', collections.Counter(u['lang'] for u in U).most_common())
