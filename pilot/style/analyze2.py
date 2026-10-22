"""Learned (not predefined) style space from same-intent / different-style pairs.
z[i,s] ~ mean + a_i + v_s   (intent offset + style offset), word2vec-offset style."""
import json, numpy as np
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr
D = json.load(open('texts.json')); items = D['items']
ds = [i for i, x in enumerate(items) if x['kind'] == 'dataset']; rl = [i for i, x in enumerate(items) if x['kind'] == 'real']
I = sorted({items[i]['intent'] for i in ds}); S = ['P', 'O', 'F', 'D', 'G']
ix = {(items[i]['intent'], items[i]['style']): k for k, i in enumerate(ds)}
corp = np.array([items[i]['corpus'] for i in rl]); CORPS = sorted(set(corp))
def grid(Z): return np.stack([[Z[ix[(a, s)]] for s in S] for a in I])  # 12 x 5 x d

def style_vecs(G, rows=None):
    G = G if rows is None else G[rows]
    C = G - G.mean(1, keepdims=True)     # remove each intent's mean over styles
    return C.mean(0)                     # 5 x d   (rank 4)

def analogy(G):
    """predict cell (b,s) = z(b,r) + mean_{a!=b}[z(a,s) - z(a,r)], r != s. Rank among 5 cells of row b (excluding r) and among all 60."""
    row_hit = []; pool_hit = []; copy_pool = []
    flat = G.reshape(-1, G.shape[-1]); lab = [(a, s) for a in range(len(I)) for s in range(5)]
    for b in range(len(I)):
        others = [a for a in range(len(I)) if a != b]
        for s in range(5):
            for r in range(5):
                if r == s: continue
                pred = G[b, r] + (G[others, s] - G[others, r]).mean(0)
                cand = [t for t in range(5) if t != r]
                row_hit.append(max(cand, key=lambda t: pred @ G[b, t]) == s)
                sims = flat @ pred; mask = np.array([not (a == b and t == r) for a, t in lab]); sims[~mask] = -9
                pool_hit.append(lab[int(sims.argmax())] == (b, s))
                sims2 = flat @ G[b, r]; sims2[~mask] = -9  # baseline: no style offset
                copy_pool.append(lab[int(sims2.argmax())] == (b, s))
    return float(np.mean(row_hit)), float(np.mean(pool_hit)), float(np.mean(copy_pool))

def basis(V):
    u, sv, vt = np.linalg.svd(V - V.mean(0), full_matrices=False); return vt[:4], sv[:4]

def cv_style_space(G):
    """held-out-intent test: style basis from 11 intents, place the held-out intent's 5 cells; nearest prototype in style subspace"""
    hit = []
    for b in range(len(I)):
        tr = [a for a in range(len(I)) if a != b]
        V = style_vecs(G, tr); B, _ = basis(V); proto = V @ B.T            # 5 x 4 prototypes
        for s in range(5):
            z = G[b, s] - G[b].mean(0); c = B @ z                          # coordinate of a held-out cell, intent mean removed
            hit.append(int(np.argmin(((proto - c)**2).sum(1))) == s)
    return float(np.mean(hit))

def cv_style_space_nocenter(G):
    """harder: held-out code is NOT given its intent-centroid (as for real new code). subtract only the global mean."""
    hit = []
    for b in range(len(I)):
        tr = [a for a in range(len(I)) if a != b]
        V = style_vecs(G, tr); B, _ = basis(V); proto = V @ B.T; gm = G[tr].mean((0, 1))
        for s in range(5):
            c = B @ (G[b, s] - gm); hit.append(int(np.argmin(((proto - c)**2).sum(1))) == s)
    return float(np.mean(hit))

out = {}; keep = {}
for model in ['unixcoder', 'qwen3', 'qwen3_lora']:
    try: E = np.load(f'emb_{model}.npz')
    except FileNotFoundError: continue
    out[model] = {}
    for var in ['raw', 'hashed']:
        Z = E[var]; G = grid(Z[ds]); r = {}
        r['analogy_row_acc'], r['analogy_pool_acc'], r['copy_baseline_pool_acc'] = analogy(G)
        r['heldout_intent_style_acc_centered'] = cv_style_space(G); r['heldout_intent_style_acc_uncentered'] = cv_style_space_nocenter(G)
        V = style_vecs(G); B, sv = basis(V)
        # prototype distances: how far apart are styles (cosine of style vectors)
        r['style_vec_cos'] = (V / np.linalg.norm(V, axis=1, keepdims=True) @ (V / np.linalg.norm(V, axis=1, keepdims=True)).T).round(2).tolist()
        r['style_vec_norm'] = np.linalg.norm(V, axis=1).round(3).tolist()
        # share of variance: intent vs style (2-way decomposition on the grid)
        X = G - G.mean((0, 1)); a = X.mean(1, keepdims=True); v = X.mean(0, keepdims=True); tot = (X**2).sum()
        r['var_intent'] = float((a**2).sum() * 5 / tot); r['var_style'] = float((v**2).sum() * 12 / tot)
        # real code: coordinates in learned style space (4-d), per corpus
        Zr = Z[rl]; gm = G.mean((0, 1)); C = (Zr - gm) @ B.T; proto = V @ B.T
        d = ((C[:, None, :] - proto[None]) ** 2).sum(-1); near = d.argmin(1)
        r['real_nearest_style_share'] = {c: {S[k]: round(float((near[corp == c] == k).mean()), 2) for k in range(5)} for c in CORPS}
        cen = {c: C[corp == c].mean(0) for c in CORPS}
        r['real_spread'] = {c: round(float(np.sqrt(((C[corp == c] - cen[c])**2).sum(1)).mean()), 3) for c in CORPS}
        # consistency check: AUROC of distance-to-own-corpus-centroid (fit on half) for held-out own (neg) vs other-corpus (pos)
        rng = np.random.default_rng(0); aucs = {}
        for c in CORPS:
            idx = np.where(corp == c)[0]; rng.shuffle(idx); fit, te = idx[:len(idx)//2], idx[len(idx)//2:]
            m = C[fit].mean(0); own = np.sqrt(((C[te] - m)**2).sum(1)); oth = np.sqrt(((C[corp != c] - m)**2).sum(1))
            aucs[c] = round(float(roc_auc_score([0]*len(own) + [1]*len(oth), np.r_[own, oth])), 2)
        r['outlier_auc'] = aucs
        # post-hoc naming of learned axes by name-free AST features on real code (NOT used to define axes)
        feats = np.array([items[i]['axes'] for i in rl])
        r['posthoc_spearman'] = {f'PC{k+1}': {n: round(float(spearmanr(C[:, k], feats[:, j])[0]), 2) for j, n in enumerate(['mutation', 'object_binding', 'explicit_iteration', 'columnar_batch'])} for k in range(4)}
        out[model][var] = r; keep[(model, var)] = (G, V, B, C, proto)
json.dump(out, open('results2.json', 'w'), indent=1, default=float)
for m in out:
    for v in out[m]:
        r = out[m][v]; print(m, v, 'analogy row %.2f pool %.2f (copy %.2f)' % (r['analogy_row_acc'], r['analogy_pool_acc'], r['copy_baseline_pool_acc']),
              '| heldout-intent style acc centered %.2f uncentered %.2f' % (r['heldout_intent_style_acc_centered'], r['heldout_intent_style_acc_uncentered']),
              '| var intent %.2f style %.2f' % (r['var_intent'], r['var_style']))
import pickle; pickle.dump(keep, open('keep.pkl', 'wb'))
