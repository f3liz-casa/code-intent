import json, sys, numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
D = json.load(open('texts.json')); items = D['items']; descs = list(D['desc'].keys())
ds = [i for i, x in enumerate(items) if x['kind'] == 'dataset']; rl = [i for i, x in enumerate(items) if x['kind'] == 'real']
intent = np.array([items[i]['intent'] for i in ds]); style = np.array([items[i]['style'] for i in ds])
AX = np.array([x['axes'] for x in items]); corp = np.array([items[i]['corpus'] for i in rl])
I_names = sorted(set(intent)); S_names = ['P', 'O', 'F', 'D', 'G']

def two_way(Z):
    mu = Z.mean(0); X = Z - mu
    im = np.stack([X[intent == i].mean(0) for i in intent]); R1 = X - im
    sm = np.stack([R1[style == s].mean(0) for s in style]); R2 = R1 - sm
    tot = (X**2).sum(); return dict(intent=(im**2).sum()/tot, style=(sm**2).sum()/tot, resid=(R2**2).sum()/tot), im, sm

def style_dirs(Z):
    """style effect vectors: mean over intents of (z[i,s] - mean_s z[i,.])"""
    X = Z.copy()
    for i in I_names: X[intent == i] -= X[intent == i].mean(0)
    return np.stack([X[style == s].mean(0) for s in S_names])  # 5 x d, rank 4

def intent_dirs(Z):
    X = Z.copy()
    for s in S_names: X[style == s] -= X[style == s].mean(0)
    return np.stack([X[intent == i].mean(0) for i in I_names])  # 12 x d (rank 11)

def subspace_overlap(A, B):
    qa = np.linalg.svd(A - A.mean(0), full_matrices=False)[2][:np.linalg.matrix_rank(A - A.mean(0), tol=1e-6)]
    qb = np.linalg.svd(B - B.mean(0), full_matrices=False)[2][:np.linalg.matrix_rank(B - B.mean(0), tol=1e-6)]
    sv = np.linalg.svd(qa @ qb.T, compute_uv=False)
    return float((sv**2).sum() / len(qa)), len(qa), len(qb), sv

def loio_style(Z):
    acc = []; 
    for i in I_names:
        tr = intent != i; te = ~tr
        clf = LogisticRegression(max_iter=2000, C=10).fit(Z[tr], style[tr]); acc.append((clf.predict(Z[te]) == style[te]).mean())
    return float(np.mean(acc))

def _basis(M):
    M = M - M.mean(0); u, sv, vt = np.linalg.svd(M, full_matrices=False); return vt[:(sv > 1e-6 * sv[0]).sum()]

def loio_style_clean(Z):
    """remove the intent subspace estimated on TRAIN intents only, then classify style on the held-out intent"""
    acc = []
    for i in I_names:
        tr = intent != i; te = ~tr; Zt = Z[tr]; it = intent[tr]; st = style[tr]
        X = Zt.copy()
        for s in S_names: X[st == s] -= X[st == s].mean(0)
        q = _basis(np.stack([X[it == j].mean(0) for j in sorted(set(it))]))
        P = lambda A: A - (A @ q.T) @ q
        clf = LogisticRegression(max_iter=2000, C=10).fit(P(Zt), st); acc.append((clf.predict(P(Z[te])) == style[te]).mean())
    return float(np.mean(acc))

def loso_intent_clean(Z):
    acc = []
    for s in S_names:
        tr = style != s; te = ~tr; Zt = Z[tr]; it = intent[tr]; st = style[tr]
        X = Zt.copy()
        for j in I_names: X[it == j] -= X[it == j].mean(0)
        q = _basis(np.stack([X[st == t].mean(0) for t in sorted(set(st))]))
        P = lambda A: A - (A @ q.T) @ q
        C = np.stack([P(Zt)[it == j].mean(0) for j in I_names])
        pred = np.array(I_names)[(P(Z[te]) @ C.T).argmax(1)]; acc.append((pred == intent[te]).mean())
    return float(np.mean(acc))

def loso_intent(Z):
    acc = []
    for s in S_names:
        tr = style != s; te = ~tr
        C = np.stack([Z[tr & (intent == i)].mean(0) for i in I_names])
        pred = np.array(I_names)[(Z[te] @ C.T).argmax(1)]; acc.append((pred == intent[te]).mean())
    return float(np.mean(acc))

def desc_retrieval(Zd, Zq):
    """description -> rank the 60 snippets; mean reciprocal rank of first correct, and P@5 by style"""
    S = Zq @ Zd.T; mrr = []; p5 = {s: [] for s in S_names}; first = {s: [] for s in S_names}
    for k, d in enumerate(descs):
        order = np.argsort(-S[k]); rel = (intent[order] == d)
        mrr.append(1 / (np.argmax(rel) + 1))
    # per-style: restrict pool to one style (12 snippets, one per intent) -> R@1
    for s in S_names:
        m = style == s; Ss = Zq @ Zd[m].T; ints = intent[m]
        first[s] = float(np.mean([ints[Ss[k].argmax()] == d for k, d in enumerate(descs)]))
    return float(np.mean(mrr)), first

def axis_probe(Z, alpha=1.0):
    P = np.zeros((len(Z), 4))
    for i in I_names:
        tr = intent != i
        P[intent == i] = Ridge(alpha=alpha).fit(Z[tr], AX[ds][tr]).predict(Z[intent == i])
    T = AX[ds]
    return [float(1 - ((T[:, a] - P[:, a])**2).sum() / (((T[:, a] - T[:, a].mean())**2).sum() + 1e-12)) for a in range(4)]

res = {}
for model in ['unixcoder', 'qwen3', 'qwen3_lora']:
    try: E = np.load(f'emb_{model}.npz')
    except FileNotFoundError: continue
    res[model] = {}
    for var in ['raw', 'hashed']:
        Z = E[var]; Zd = Z[ds]; r = {}
        r['variance'], _, _ = [(a) for a in two_way(Zd)]
        SD, ID = style_dirs(Zd), intent_dirs(Zd)
        ov, ka, kb, sv = subspace_overlap(SD, ID); r['overlap_style_intent'] = ov; r['dims'] = [ka, kb]
        rng = np.random.default_rng(0); d = Zd.shape[1]
        r['overlap_random_expect'] = float(kb / d)
        r['style_acc_loio'] = loio_style(Zd); r['intent_acc_loso'] = loso_intent(Zd)
        # remove style subspace -> intent still found?  remove intent subspace -> style still found?
        qs = np.linalg.svd(SD - SD.mean(0), full_matrices=False)[2][:4]; qi = np.linalg.svd(ID - ID.mean(0), full_matrices=False)[2][:11]
        Zns = Zd - (Zd @ qs.T) @ qs; Zni = Zd - (Zd @ qi.T) @ qi
        r['style_acc_after_removing_intent_subspace'] = loio_style_clean(Zd); r['intent_acc_after_removing_style_subspace'] = loso_intent_clean(Zd)
        Q = E['desc']
        mrr, first = desc_retrieval(Zd, Q); r['desc_mrr'] = mrr; r['desc_r1_by_style'] = first
        r['axis_r2_loio'] = axis_probe(Zd)
        res[model][var] = r
json.dump(res, open("results.json","w"), indent=1, default=float)
for m in res:
    for v in res[m]:
        r = res[m][v]
        print(m, v, 'var', {k: round(x, 3) for k, x in r['variance'].items()}, 'ovl %.3f (rand %.3f)' % (r['overlap_style_intent'], r['overlap_random_expect']),
              'styleAcc %.2f intentAcc %.2f' % (r['style_acc_loio'], r['intent_acc_loso']),
              'noI-styleAcc %.2f noS-intentAcc %.2f' % (r['style_acc_after_removing_intent_subspace'], r['intent_acc_after_removing_style_subspace']),
              'descMRR %.2f' % r['desc_mrr'], 'axisR2', np.round(r['axis_r2_loio'], 2))
