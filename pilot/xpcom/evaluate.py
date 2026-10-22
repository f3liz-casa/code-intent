import json, numpy as np
V = json.load(open('variants.json')); n = len(V['pairs']); decoy = np.array(V['decoy_index'])
CONDS = [('C0 raw JS vs raw C++', 'js_raw', 'cpp_raw'), ('C1 JS name masked', 'js_indep', 'cpp_raw'), ('C2 C++ name masked', 'js_raw', 'cpp_indep'),
         ('C3 name masked, same hash both sides', 'js_same', 'cpp_same'), ('C4 name masked, different hashes', 'js_indep', 'cpp_indep'),
         ('C5 all identifiers hashed, consistent', 'js_allcons', 'cpp_allcons'), ('C6 all identifiers hashed, salted per language', 'js_allsalt', 'cpp_allsalt'),
         ('C7 names only', 'js_name', 'cpp_name')]
def metrics(J, C, idx=None):
    S = J @ C.T; order = np.argsort(-S, 1); rank = np.array([np.where(order[i] == i)[0][0] + 1 for i in range(len(J))])
    return dict(r1=float((rank == 1).mean()), r10=float((rank <= 10).mean()), mrr=float((1 / rank).mean())), rank
def boot(rank, B=500, seed=0):
    rng = np.random.default_rng(seed); r1 = [(rank[rng.integers(0, len(rank), len(rank))] == 1).mean() for _ in range(B)]
    return [float(np.percentile(r1, 2.5)), float(np.percentile(r1, 97.5))]
out = {}
for model in ['unixcoder', 'qwen3']:
    try: E = np.load(f'emb_{model}.npz')
    except FileNotFoundError: continue
    o = {}
    A = np.arange(n) % 2 == 0; B = ~A
    for name, jk, ck in CONDS:
        J, C = E[jk], E[ck]; m, rank = metrics(J, C); m['r1_ci'] = boot(rank)
        # language offset estimated on half A, evaluated on half B (pool = B only), and the reverse
        res = []
        for tr, te in ((A, B), (B, A)):
            off = C[tr].mean(0) - J[tr].mean(0)
            Jt = J[te] + off; Jt /= np.linalg.norm(Jt, axis=1, keepdims=True)
            m0, _ = metrics(J[te], C[te]); m1, _ = metrics(Jt, C[te]); res.append((m0['mrr'], m1['mrr'], m0['r1'], m1['r1']))
        m['half_pool_mrr_no_offset'] = float(np.mean([r[0] for r in res])); m['half_pool_mrr_with_offset'] = float(np.mean([r[1] for r in res]))
        m['half_pool_r1_no_offset'] = float(np.mean([r[2] for r in res])); m['half_pool_r1_with_offset'] = float(np.mean([r[3] for r in res]))
        m['mean_cos_matched'] = float(np.mean(np.sum(J * C, 1))); m['mean_cos_unmatched'] = float(np.mean(J @ C.T - np.diag(np.diag(J @ C.T)) * 1.0) * n / (n - 1))
        o[name] = m
    # decoy: JS with name replaced by another interface method name; where does the retrieval go?
    S = E['js_decoy'] @ E['cpp_raw'].T; top = S.argmax(1)
    o['C8 decoy name in JS'] = dict(top1_is_original=float((top == np.arange(n)).mean()), top1_is_decoy_cpp=float((top == decoy).mean()))
    out[model] = o
json.dump(out, open('results.json', 'w'), indent=1)
for model, o in out.items():
    print('==', model, '(N=%d, chance R@1 %.3f, chance MRR ~%.3f)' % (n, 1 / n, sum(1 / k for k in range(1, n + 1)) / n))
    for k, m in o.items():
        if 'r1' in m: print('  %-50s R@1 %.2f [%.2f,%.2f] R@10 %.2f MRR %.2f | half-pool MRR %.2f -> %.2f with language offset | cos match %.2f vs other %.2f' % (k, m['r1'], *m['r1_ci'], m['r10'], m['mrr'], m['half_pool_mrr_no_offset'], m['half_pool_mrr_with_offset'], m['mean_cos_matched'], m['mean_cos_unmatched']))
        else: print('  %-50s %s' % (k, {a: round(b, 2) for a, b in m.items()}))
