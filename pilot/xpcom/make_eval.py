import json, re, random, collections
random.seed(0)
I = json.load(open('index.json')); iface = I['interfaces']; decl = I['methods']
def chain(i):
    out = []
    while i in iface and i not in out: out.append(i); i = iface[i]['base']
    return out
sites = [json.loads(l) for l in open('js_sites.jsonl')]
ev = []; seen = set(); per = collections.Counter()
random.shuffle(sites)
for s in sites:
    cands = decl[s['method']]
    if len(cands) < 2: continue
    truth = [c for c in cands if any(c in chain(h) for h in s['hints'] if h in iface)]
    if len(truth) != 1: continue
    k = (s['file'], s['line'], s['method'])
    if k in seen or per[s['method']] >= 15: continue
    seen.add(k); per[s['method']] += 1
    masked = re.sub(r'\bnsI[A-Z]\w+\b', 'nsIX', s['code'])
    ev.append(dict(method=s['method'], file=s['file'], line=s['line'], recv=s['recv'], cands=cands, truth=truth[0], masked=masked))
print('eval sites', len(ev), 'methods', len(per), 'cand-set size median', sorted(len(e['cands']) for e in ev)[len(ev) // 2], 'chance acc %.3f' % (sum(1 / len(e['cands']) for e in ev) / len(ev)))
print(per.most_common(8))
itexts = {n: f"{n}\n{d['doc']}\nmethods: {', '.join(d['methods'][:30])}" for n, d in iface.items()}
json.dump(dict(eval=ev, itexts=itexts), open('eval_sites.json', 'w'))
