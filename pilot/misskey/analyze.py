"""Indicators over the Misskey units/files extracted by extract.mjs. usage: python3 -I analyze.py <extract out dir> <result dir>"""
import json, sys, re, math, collections, random
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
U = [json.loads(l) for l in open(f'{src}/units.jsonl')]
F = [json.loads(l) for l in open(f'{src}/files.jsonl')]
rng = np.random.default_rng(0); random.seed(0)
out = {}
def P(*a):
    print(*a)

# ---- category from reachable platform/domain leaves -------------------------------------------------
WRITE = {'db.write', 'redis.write', 'fs'}
EMIT = {'event.publish', 'queue.enqueue', 'federation.ap', 'net.http', 'audit.log'}
READ = {'db.read', 'redis.read', 'redis.other', 'api.call', 'pack.entity'}
DELEG = {'service.call'}
UI = {'ui.dialog', 'nav', 'vue.emit', 'i18n'}
STATE = {'vue.state', 'local.state', 'dom', 'stream'}
# reachable leaves: follow this.x(...) inside a class and bare helper calls inside a file (same idea as asttok.py)
byk = {}
for u in U:
    byk.setdefault((u['file'], u['cls'], u['name']), u)
    byk.setdefault((u['file'], None, u['name']), u)
for u in U:
    u['rl'] = set(u['leaves']); u['tgt'] = []
    for c in u['callees']:
        if c.startswith('this.') and '.' not in c[5:]: t = byk.get((u['file'], u['cls'], c[5:]))
        elif '.' not in c: t = byk.get((u['file'], None, c))
        else: t = None
        if t is not None and t is not u: u['tgt'].append(t)
for _ in range(6):
    ch = False
    for u in U:
        for t in u['tgt']:
            if not t['rl'] <= u['rl']: u['rl'] |= t['rl']; ch = True
    if not ch: break
def category(u):
    L = u['rl']
    if L & WRITE: return 'write'
    if L & EMIT: return 'emit'
    if L & READ: return 'read'
    if L & DELEG: return 'delegate'
    if L & UI: return 'ui'
    if L & STATE: return 'state'
    return 'pure'
for u in U: u['cat'] = category(u)
U = [u for u in U if u['loc'] >= 3]
P('units', len(U), collections.Counter(u['cat'] for u in U))
LAYERS = [l for l, n in collections.Counter(u['layer'] for u in U).most_common() if n >= 40]

def H(counter):
    n = sum(counter.values()); return -sum(c / n * math.log2(c / n) for c in counter.values() if c) if n else 0.0

# ---- style: unsupervised clusters over structure-only features (no names, no leaves) ------------------
def feats(u):
    n = max(u['loc'], 1)
    return [math.log1p(u['loops']), math.log1p(u['chain']), math.log1p(u['mutate']), u['lets'] / (u['lets'] + u['consts'] + 1e-9) if (u['lets'] + u['consts']) else 0.0,
            math.log1p(u['awaits']), math.log1p(u['thens']), float(u['thisUse'] > 0), float(u['cls'] is not None), math.log1p(u['sw']), math.log1p(u['tern']),
            math.log1p(u['tries']), math.log1p(u['throws']), math.log1p(u['maxDepth']), math.log1p(u['loc']), math.log1p(u['cyc']) , math.log1p(u['opt']), math.log1p(u['nonNull'])]
FN = ['loops', 'chain', 'mutate', 'let_share', 'awaits', 'thens', 'uses_this', 'in_class', 'switch', 'ternary', 'try', 'throw', 'depth', 'loc', 'cyc', 'optional', 'nonnull']
X = np.array([feats(u) for u in U]); mu, sd = X.mean(0), X.std(0) + 1e-9; Z = (X - mu) / sd
def kmeans(Z, k, it=60, seed=0):
    r = np.random.default_rng(seed); C = Z[r.choice(len(Z), k, replace=False)]
    for _ in range(it):
        d = ((Z[:, None, :] - C[None]) ** 2).sum(-1); a = d.argmin(1)
        C2 = np.array([Z[a == j].mean(0) if (a == j).any() else C[j] for j in range(k)])
        if np.allclose(C, C2): break
        C = C2
    return a, C, d.min(1).sum()
K = 7
best = min((kmeans(Z, K, seed=s) for s in range(8)), key=lambda t: t[2])
A, C, _ = best
names = {}
for j in range(K):
    top = np.argsort(-np.abs(C[j]))[:3]
    names[j] = f's{j}:' + ','.join(('+' if C[j][t] > 0 else '-') + FN[t] for t in top)
    P(names[j], (A == j).sum())
for u, a in zip(U, A): u['style'] = int(a)
out['style_clusters'] = {names[j]: int((A == j).sum()) for j in range(K)}

# ---- 1. layer x style placement ---------------------------------------------------------------------
mat = {}
for l in LAYERS:
    c = collections.Counter(u['style'] for u in U if u['layer'] == l); n = sum(c.values())
    mat[l] = {names[j]: round(c[j] / n, 3) for j in range(K)}
out['layer_style'] = mat
out['layer_style_entropy_bits'] = {l: round(H(collections.Counter(u['style'] for u in U if u['layer'] == l)), 2) for l in LAYERS}
out['layer_cat'] = {l: dict(collections.Counter(u['cat'] for u in U if u['layer'] == l)) for l in LAYERS}
P('H(style|layer)', out['layer_style_entropy_bits'])

# ---- 2. does style carry category inside a layer?  MI(style;cat | layer) vs shuffled -------------------
def mi_within(units, shuffle=False):
    tot = 0.0; n = len(units)
    for l in LAYERS:
        us = [u for u in units if u['layer'] == l]
        if len(us) < 40: continue
        s = [u['style'] for u in us]; c = [u['cat'] for u in us]
        if shuffle: random.shuffle(c)
        hs = H(collections.Counter(s)); hj = H(collections.Counter(zip(s, c))); hc = H(collections.Counter(c))
        tot += len(us) / n * (hs + hc - hj)
    return tot
mi = mi_within(U); null = [mi_within(U, True) for _ in range(200)]
out['MI_style_cat_given_layer'] = {'observed_bits': round(mi, 4), 'shuffle_mean': round(float(np.mean(null)), 4), 'shuffle_p99': round(float(np.percentile(null, 99)), 4)}
per = {}
for l in LAYERS:
    us = [u for u in U if u['layer'] == l]
    s = [u['style'] for u in us]; c = [u['cat'] for u in us]
    obs = H(collections.Counter(s)) + H(collections.Counter(c)) - H(collections.Counter(zip(s, c)))
    nl = []
    for _ in range(200):
        cc = c[:]; random.shuffle(cc); nl.append(H(collections.Counter(s)) + H(collections.Counter(cc)) - H(collections.Counter(zip(s, cc))))
    per[l] = {'n': len(us), 'mi': round(obs, 3), 'null_mean': round(float(np.mean(nl)), 3), 'z': round((obs - np.mean(nl)) / (np.std(nl) + 1e-9), 1)}
out['MI_per_layer'] = per
P('MI', out['MI_style_cat_given_layer']); [P(l, v) for l, v in per.items()]

# ---- 3. declared-convention adherence --------------------------------------------------------------
vue = [f for f in F if 'vue' in f and f['layer'].startswith('fe')]
fe_vue = [f for f in vue if f['file'].startswith('packages/frontend/src/')]
def rate(xs, pred): xs = list(xs); k = sum(1 for x in xs if pred(x)); return {'n': len(xs), 'ok': k, 'rate': round(k / max(len(xs), 1), 3)}
conv = {}
conv['vue: <script setup lang=ts>'] = rate(fe_vue, lambda f: f['vue']['scriptSetup'] and f['vue']['langTs'])
conv['vue: type-only defineProps (among files with props)'] = rate([f for f in fe_vue if f['vue']['defineProps'] != 'none'], lambda f: f['vue']['defineProps'] == 'type')
conv['vue: type-only defineEmits (among files with emits)'] = rate([f for f in fe_vue if f['vue']['defineEmits'] != 'none'], lambda f: f['vue']['defineEmits'] == 'type')
conv['vue: scss module (among files with style)'] = rate([f for f in fe_vue if f['vue']['nStyle']], lambda f: f['vue']['styleModule'])
conv['vue: no native alert/confirm/prompt'] = rate(fe_vue, lambda f: not f['vue']['nativeAlert'])
conv['vue: no literal text nodes (i18n)'] = rate(fe_vue, lambda f: f['vue']['rawTextNodes'] == 0)
conv['vue: Options API leftovers'] = rate(fe_vue, lambda f: f['vue']['optionsApi'])
conv['spdx header (all)'] = rate(F, lambda f: f['spdx'])
be = [f for f in F if f['file'].startswith('packages/backend/src/')]
svc = [f for f in F if f['layer'] in ('be:service', 'be:activitypub', 'be:queue-processor', 'be:server')]
conv['be: service files with @Injectable'] = rate([f for f in F if f['layer'] == 'be:service' and f['classes']], lambda f: f['injectable'])
conv['be: endpoints extend Endpoint'] = rate([f for f in F if f['layer'] == 'be:endpoint' and not f['file'].endswith('endpoint-list.ts')], lambda f: f['endpoint'])
conv['be: injectable classes using @bindThis'] = rate([f for f in be if f['injectable'] and any(c['nMethods'] > 0 for c in f['classes'])], lambda f: f['hasBindThis'])
conv['be: files with `any`'] = rate(be, lambda f: f['anyKw'] == 0)
conv['all: no @ts-ignore/@ts-expect-error'] = rate(F, lambda f: f['tsIgnore'] == 0)
# DI: repositories injected via @Inject(DI.x) in the ctor, services by type
cp = collections.Counter()
for f in svc:
    for c in f['classes']:
        for p in c['ctorParams']:
            t = p['type']
            if 'Repository' in t: cp['repo:' + ('inject' if any('DI.' in d for d in p['deco']) else 'type-only')] += 1
            elif t.endswith('Service'): cp['service:' + ('inject' if p['deco'] else 'type-only')] += 1
conv['_ctor param styles'] = dict(cp)
out['conventions'] = conv
P(json.dumps(conv, indent=1)[:3000])

# ---- 4. name vs behaviour ---------------------------------------------------------------------------
def nwords(u): return [w for w in re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', u['name'] or '') ]
def first(u):
    w = nwords(u); return w[0].lower() if w else ''
READV = {'get', 'find', 'fetch', 'list', 'is', 'has', 'can', 'check', 'count', 'search', 'show', 'pack', 'should', 'to', 'parse', 'resolve', 'validate', 'build', 'calc', 'compute'}
WRITEV = {'create', 'update', 'delete', 'remove', 'set', 'add', 'save', 'insert', 'register', 'unregister', 'follow', 'unfollow', 'mute', 'block', 'post', 'publish', 'send', 'delivery', 'deliver', 'upload', 'import', 'export', 'clear', 'reset'}
mism = {}
verbs = collections.defaultdict(lambda: collections.Counter())
for u in U:
    if u['name'] and u['name'] not in ('<handler>',): verbs[first(u)][u['cat']] += 1
vt = {v: dict(c) for v, c in verbs.items() if sum(c.values()) >= 12}
out['verb_vs_category'] = vt
side = lambda u: u['cat'] in ('write', 'emit')
for grp, vs, bad, desc in [('read-verb performs write/emit', READV, side, 'getter-like names that write or emit'), ('write-verb performs nothing observable', WRITEV, lambda u: u['cat'] in ('pure', 'read'), 'mutator-like names whose reachable effects are only read/pure (delegation to other services is not counted as a mismatch)')]:
    xs = [u for u in U if first(u) in vs and u['layer'] in LAYERS and u['name'] != '<handler>']
    bs = [u for u in xs if bad(u)]
    mism[grp] = {'n': len(xs), 'mismatch': len(bs), 'rate': round(len(bs) / max(len(xs), 1), 3), 'desc': desc,
                 'examples': [f"{u['file'].split('/src/')[-1]}:{u['line']} {u['cls'] or ''}.{u['name']} [{','.join(sorted(u['rl']))}]" for u in sorted(bs, key=lambda u: -u['loc'])[:8]]}
out['name_vs_effect'] = mism
P(json.dumps(mism, indent=1, ensure_ascii=False)[:3500])

# name-only vs structure-only vs both: Naive Bayes for category, 5-fold grouped by file
files_ = sorted({u['file'] for u in U}); random.shuffle(files_); fold = {f: i % 5 for i, f in enumerate(files_)}
def tok_name(u): return ['n:' + w.lower() for w in nwords(u)] + (['n1:' + first(u)] if first(u) else [])
def tok_layer(u): return ['L:' + u['layer']]
def tok_struct(u):
    t = []
    for k in ('loops', 'chain', 'mutate', 'awaits', 'thens', 'sw', 'tern', 'tries', 'throws', 'opt'):
        v = u[k]; t.append(f's:{k}={0 if v == 0 else (1 if v == 1 else (2 if v < 4 else 3))}')
    t.append('s:loc=' + str(min(int(math.log2(u['loc'])), 7))); t.append('s:async=' + str(u['async'])); t.append('s:cls=' + str(u['cls'] is not None)); t.append('s:np=' + str(min(u['nparams'], 4)))
    t.append('s:ret=' + (u['rtype'][:14] or 'none')); t.extend('s:deco=' + d for d in u['decos'])
    return t
def nb_eval(tokf):
    cats = sorted({u['cat'] for u in U}); correct = 0; byc = collections.Counter(); tot = collections.Counter()
    for k in range(5):
        tr = [u for u in U if fold[u['file']] != k]; te = [u for u in U if fold[u['file']] == k]
        prior = collections.Counter(u['cat'] for u in tr); cnt = {c: collections.Counter() for c in cats}; vocab = set()
        for u in tr:
            for t in set(tokf(u)): cnt[u['cat']][t] += 1; vocab.add(t)
        for u in te:
            best, bs = None, -1e18
            for c in cats:
                s = math.log(prior[c] / len(tr))
                for t in set(tokf(u)):
                    if t in vocab: s += math.log((cnt[c][t] + 0.5) / (prior[c] + 1))
                if s > bs: best, bs = c, s
            tot[u['cat']] += 1
            if best == u['cat']: correct += 1; byc[u['cat']] += 1
    rec = {c: round(byc[c] / tot[c], 2) for c in tot}
    return {'acc': round(correct / len(U), 3), 'macro_recall': round(sum(rec.values()) / len(rec), 3), 'recall': rec}
maj = collections.Counter(u['cat'] for u in U).most_common(1)[0]
nbres = {'majority': round(maj[1] / len(U), 3)}
for nm, f in [('layer', tok_layer), ('name', tok_name), ('structure', tok_struct), ('layer+name', lambda u: tok_layer(u) + tok_name(u)), ('layer+structure', lambda u: tok_layer(u) + tok_struct(u)), ('name+structure', lambda u: tok_name(u) + tok_struct(u)), ('layer+name+structure', lambda u: tok_layer(u) + tok_name(u) + tok_struct(u))]:
    nbres[nm] = nb_eval(f)
out['category_predictors'] = nbres
P('NB', json.dumps(nbres, indent=1))

# ---- 5. convention drift: outliers in structure space within layer -----------------------------------
outl = {}
for l in LAYERS:
    idx = [i for i, u in enumerate(U) if u['layer'] == l]
    if len(idx) < 40: continue
    Zl = Z[idx]; cen = np.median(Zl, 0); d = np.sqrt(((Zl - cen) ** 2).sum(1))
    thr = np.percentile(d, 95); ordr = np.argsort(-d)[:4]
    outl[l] = [{'where': f"{U[idx[i]]['file'].split('/src/')[-1]}:{U[idx[i]]['line']}", 'unit': f"{U[idx[i]]['cls'] or ''}.{U[idx[i]]['name']}", 'why': [FN[t] for t in np.argsort(-np.abs(Zl[i] - cen))[:3]], 'dist': round(float(d[i]), 1)} for i in ordr]
out['outliers'] = outl

# file-level drift: share of units in a file whose style cluster differs from the layer's modal cluster
ff = collections.defaultdict(list)
for u in U: ff[u['file']].append(u)
modal = {l: collections.Counter(u['style'] for u in U if u['layer'] == l).most_common(1)[0][0] for l in LAYERS}
hom = {}
for l in LAYERS:
    xs = [fs for f, fs in ff.items() if fs[0]['layer'] == l and len(fs) >= 4]
    if not xs: continue
    within = np.mean([H(collections.Counter(u['style'] for u in fs)) for fs in xs])
    hom[l] = {'files': len(xs), 'mean_within_file_style_entropy': round(float(within), 2), 'layer_entropy': out['layer_style_entropy_bits'][l]}
out['file_homogeneity'] = hom

# ---- 6. documentation of intent -----------------------------------------------------------------------
doc = {}
for c in sorted({u['cat'] for u in U}):
    xs = [u for u in U if u['cat'] == c]; doc[c] = round(sum(u['hasDoc'] for u in xs) / len(xs), 3)
cx = [u for u in U if u['cyc'] >= 12]
doc_by_layer = {l: {'cyc>=12': sum(1 for u in cx if u['layer'] == l), 'undocumented': round(sum(1 for u in cx if u['layer'] == l and not u['hasDoc']) / max(1, sum(1 for u in cx if u['layer'] == l)), 2)} for l in LAYERS}
out['doc_by_category'] = doc; out['complex_undocumented_by_layer'] = doc_by_layer
P('doc', doc)

# ---- 7. domain vocabulary and synonym spread ------------------------------------------------------------
wc = collections.Counter(); wlay = collections.defaultdict(collections.Counter)
for u in U:
    for w in set(x.lower() for x in nwords(u)): wc[w] += 1; wlay[w][u['layer'].split(':')[0]] += 1
idw = collections.Counter()
for u in U:
    for c in u['callees']:
        for w in re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])', c): idw[w.lower()] += 1
CONC = {'note': ['note', 'post', 'status', 'toot'], 'renote': ['renote', 'boost', 'repost', 'reblog', 'announce'], 'reaction': ['reaction', 'like', 'favourite', 'favorite'],
        'emoji': ['emoji', 'emote', 'emoticon'], 'user': ['user', 'account', 'actor', 'person'], 'follow': ['follow', 'following', 'follower', 'subscribe'], 'instance': ['instance', 'server', 'host', 'domain'],
        'remote': ['remote', 'foreign', 'external', 'federated'], 'drive': ['drive', 'file', 'attachment', 'media'], 'timeline': ['timeline', 'feed', 'stream'], 'channel': ['channel', 'group', 'community'],
        'moderation': ['moderat', 'abuse', 'report', 'suspend', 'silence', 'block', 'mute'], 'activitypub': ['activity', 'inbox', 'outbox', 'actor', 'webfinger', 'ap']}
voc = {}
for k, ws in CONC.items():
    voc[k] = {w: int(wc.get(w, 0)) for w in ws}
out['concept_word_counts_in_unit_names'] = voc
out['top_name_words'] = wc.most_common(60)
# words that appear in only one of backend/frontend vs both
both = [w for w, c in wc.items() if wlay[w]['be'] >= 5 and wlay[w]['fe'] >= 5]
out['shared_vocab_be_fe'] = len(both); out['vocab_size_ge5'] = sum(1 for w, c in wc.items() if c >= 5)
# abbreviations: very short parameter-like identifiers inside call chains
short = collections.Counter()
for u in U:
    for c in u['callees']:
        h = c.split('.')[0]
        if 0 < len(h) <= 2 and h.isalpha(): short[h] += 1
out['short_receivers'] = short.most_common(12)

# ---- 8. one-glance Intent card for a few units ------------------------------------------------------------
def card(u):
    return {'where': f"{u['file'].split('/src/')[-1]}:{u['line']}", 'unit': f"{u['cls'] or ''}.{u['name']}", 'layer': u['layer'], 'category': u['cat'], 'leaves': sorted(u['rl']), 'style': names[u['style']], 'cyc': u['cyc'], 'doc': u['hasDoc']}
pick = []
for l, cat in [('be:service', 'write'), ('be:service', 'emit'), ('be:endpoint', 'read'), ('be:activitypub', 'read'), ('be:queue-processor', 'emit'), ('fe:component', 'ui'), ('fe:page', 'read'), ('fe:util', 'pure')]:
    xs = [u for u in U if u['layer'] == l and u['cat'] == cat and 10 <= u['loc'] <= 60]
    if xs: pick.append(card(random.choice(xs)))
out['cards'] = pick
json.dump(out, open(f'{dst}/results.json', 'w'), indent=1, ensure_ascii=False)

with open(f'{dst}/unit_styles.jsonl', 'w') as f:
    for u in U:
        f.write(json.dumps({'file': u['file'], 'line': u['line'], 'cls': u['cls'], 'name': u['name'], 'layer': u['layer'], 'cat': u['cat'],
                            'style': names[u['style']], 'loc': u['loc'], 'cyc': u['cyc'], 'async': u['async'], 'hasDoc': u['hasDoc'],
                            'leaves': sorted(u['rl'])}) + '\n')
