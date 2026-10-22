import json, re, numpy as np, collections
I = json.load(open('index2.json')); decl = I['methods']; impls = I['impls']
P = json.load(open('variants.json'))['pairs']
def words(s): return {w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+', s) if len(w) > 2 and w.lower() not in ('nsi', 'impl', 'the', 'ns')}
STOP = words('xpcom service component object base listener manager handler')
rows = []
for p in P:
    nm = p['name']; cs = []; seen = set()
    for i in decl.get(nm, []):
        for x in impls.get(i, {}).get(nm, []):
            k = (x['cls'], x['file'])
            if k not in seen: seen.add(k); cs.append(x)
    true = [k for k, c in enumerate(cs) if c['cls'] == p['cpp_cls'] and c['file'] == p['cpp_file']]
    if true and len(cs) >= 2: rows.append((p, cs, true[0]))
print('pairs in the index whose candidate set has >=2 implementations:', len(rows))
jsw = lambda p: words(p['js'])
def acc(scorefn):
    out = []
    for p, cs, t in rows:
        s = np.array([scorefn(p, c) for c in cs], float); best = np.flatnonzero(s == s.max()); out.append(1 / len(best) if t in best else 0.0)
    return float(np.mean(out))
print('random inside the set %.2f' % np.mean([1 / len(cs) for _, cs, _ in rows]))
print('JS words ∩ class-name words %.2f' % acc(lambda p, c: len(jsw(p) & (words(c['cls']) - STOP))))
print('JS words ∩ (class + file-path words) %.2f' % acc(lambda p, c: len(jsw(p) & (words(c['cls']) | words(c['file'])) )))
print('JS file-path words ∩ C++ file-path words %.2f' % acc(lambda p, c: len(words(p['js_file']) & words(c['file']))))
print('class implements the interface the JS function mentions (hint-style) n/a here')
