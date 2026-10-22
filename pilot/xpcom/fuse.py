import json, numpy as np
exec(open('w2v_eval.py').read().split("res = {}")[0])
E_ = np.load('emb_qwen3.npz'); U_ = np.load('emb_unixcoder.npz')
z = lambda S: (S - S.mean()) / S.std()
out = {}
for name, jk, ck in CONDS[:4]:
    Sq = E_[jk] @ E_[ck].T; Su = U_[jk] @ U_[ck].T
    St = sparse_sim(tfidf_mat(T[jk]), tfidf_mat(T[ck]))
    Jw = np.stack([bag(t, FF, True) for t in T[jk]]); Cw = np.stack([bag(t, FF, True) for t in T[ck]]); Sw = Jw @ Cw.T
    out[name] = {k: metr(S) for k, S in {'qwen3': Sq, 'tfidf-words': St, 'w2v-firefox idf': Sw, 'qwen3+tfidf': z(Sq) + z(St), 'qwen3+w2v': z(Sq) + z(Sw), 'qwen3+tfidf+w2v': z(Sq) + z(St) + z(Sw), 'unixcoder+tfidf': z(Su) + z(St)}.items()}
    print(name); [print('   %-18s R@1 %.2f R@10 %.2f MRR %.2f' % (k, v['r1'], v['r10'], v['mrr'])) for k, v in out[name].items()]
json.dump(out, open('fusion_results.json', 'w'), indent=1)
