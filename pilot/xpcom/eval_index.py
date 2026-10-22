import json, re, numpy as np, collections
I = json.load(open('index.json')); iface = I['interfaces']; impls = I['impls']
D = json.load(open('eval_sites.json')); ev = D['eval']; E = np.load('emb_index.npz'); names = list(E['names']); ni = {n: i for i, n in enumerate(names)}
def words(s): return {w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+', re.sub(r'\bnsI(?=[A-Z])', '', s)) if len(w) > 2}
def chain(i):
    out = []
    while i in iface and i not in out: out.append(i); i = iface[i]['base']
    return out
# leave-site-out frequency prior over all eval-style sites
freq = collections.defaultdict(collections.Counter)      # (method) -> truth interface counts per file, so the prior can leave out the site's own file
for e in ev: freq[e['method']][(e['truth'], e['file'])] += 1
def scores(e, k):
    C = e['cands']; rw = words(e['recv'])
    if k == 'prior': return np.array([sum(v for (t, f), v in freq[e['method']].items() if t == c and f != e['file']) for c in C], float)
    if k == 'receiver words': return np.array([len(rw & set().union(*[words(a) for a in chain(c)])) for c in C], float)
    if k == 'C++ class words': return np.array([max([len(rw & words(x['cls'])) for x in impls.get(c, {}).get(e['method'], [])] or [0]) for c in C], float)
    if k == 'Qwen3 (site vs interface text)': return np.array([E['sites'][ev.index(e) if False else e['_i']] @ E['ifaces'][ni[c]] for c in C])
for i, e in enumerate(ev): e['_i'] = i
z = lambda s: (s - s.mean()) / (s.std() + 1e-9)
KS = ['prior', 'receiver words', 'C++ class words', 'Qwen3 (site vs interface text)']
def acc(fn, rng=np.random.default_rng(0)):
    out = []
    for e in ev:
        s = fn(e); t = e['cands'].index(e['truth']); best = np.flatnonzero(s == s.max()); out.append((1.0 / len(best)) if t in best else 0.0)
    return np.array(out)
R = {'chance': np.array([1 / len(e['cands']) for e in ev])}
for k in KS: R[k] = acc(lambda e, k=k: scores(e, k))
R['receiver + C++ class words'] = acc(lambda e: z(scores(e, 'receiver words')) + z(scores(e, 'C++ class words')) + 1e-6 * z(scores(e, 'Qwen3 (site vs interface text)')))
R['Qwen3 + receiver + C++ class'] = acc(lambda e: z(scores(e, 'Qwen3 (site vs interface text)')) + z(scores(e, 'receiver words')) + z(scores(e, 'C++ class words')))
R['prior + Qwen3 + receiver + C++ class'] = acc(lambda e: z(scores(e, 'prior')) + z(scores(e, 'Qwen3 (site vs interface text)')) + z(scores(e, 'receiver words')) + z(scores(e, 'C++ class words')))
R['Qwen3 + receiver'] = acc(lambda e: z(scores(e, 'Qwen3 (site vs interface text)')) + z(scores(e, 'receiver words')))
sz = np.array([len(e['cands']) for e in ev]); b = {'2 candidates': sz == 2, '3-4': (sz >= 3) & (sz <= 4), '5+': sz >= 5}
print('N=%d eval sites over %d methods' % (len(ev), len({e['method'] for e in ev})))
print('%-34s %6s %s' % ('resolver', 'all', '  '.join(f'{k:>12}' for k in b)))
for k, v in R.items(): print('%-34s %6.2f %s' % (k, v.mean(), '  '.join(f'{v[m].mean():>12.2f}' for m in b.values())))
print('bucket sizes', {k: int(m.sum()) for k, m in b.items()})
# bootstrap CI for key resolvers
rng = np.random.default_rng(1)
for k in ['chance', 'receiver words', 'Qwen3 (site vs interface text)', 'Qwen3 + receiver + C++ class']:
    bs = [R[k][rng.integers(0, len(ev), len(ev))].mean() for _ in range(500)]; print('  95%% CI %-32s [%.2f, %.2f]' % (k, *np.percentile(bs, [2.5, 97.5])))
json.dump({k: float(v.mean()) for k, v in R.items()}, open('index_results.json', 'w'), indent=1)
