import json, re, numpy as np, collections
from gensim.models import Word2Vec, KeyedVectors
from w2v_words import words
V = json.load(open('variants.json')); T = V['texts']; n = len(V['pairs']); decoy = np.array(V['decoy_index'])
FF = Word2Vec.load('w2v_firefox.model').wv
GN = KeyedVectors.load('/tmp/w/w2v_gn/word2vec-google-news-300.model')
sent = json.load(open('w2v_sentences.json')); df = collections.Counter(w for s in sent for w in set(s)); N = len(sent)
idf = lambda w: np.log((N + 1) / (df.get(w, 0) + 1)) + 1
def bag(text, kv, weighted, lower=True):
    ws = words(text); vs = []; wt = []
    for w in ws:
        k = w if w in kv else (w.capitalize() if w.capitalize() in kv else None)
        if k is not None: vs.append(kv[k]); wt.append(idf(w) if weighted else 1.0)
    if not vs: return np.zeros(kv.vector_size)
    v = np.average(vs, axis=0, weights=wt); return v / (np.linalg.norm(v) + 1e-9)
# TF-IDF over identifier words (symbolic baseline, vocabulary from Firefox corpus idf)
def tfidf(text):
    c = collections.Counter(words(text)); return c
def tfidf_mat(texts):
    vocab = {}; rows = []
    for t in texts:
        c = tfidf(t); rows.append(c)
        for w in c: vocab.setdefault(w, len(vocab))
    return rows
CONDS = [('C0 raw', 'js_raw', 'cpp_raw'), ('C1 JS name masked', 'js_indep', 'cpp_raw'), ('C2 C++ name masked', 'js_raw', 'cpp_indep'), ('C4 name masked, different hashes', 'js_indep', 'cpp_indep'),
         ('C5 all identifiers hashed', 'js_allcons', 'cpp_allcons'), ('C7 names only', 'js_name', 'cpp_name')]
def sparse_sim(Ja, Ca):
    S = np.zeros((len(Ja), len(Ca)))
    for i, a in enumerate(Ja):
        for j, b in enumerate(Ca):
            ks = set(a) & set(b)
            S[i, j] = sum(a[k] * b[k] * idf(k) ** 2 for k in ks)
    na = np.array([np.sqrt(sum((v * idf(k)) ** 2 for k, v in a.items())) + 1e-9 for a in Ja]); nb = np.array([np.sqrt(sum((v * idf(k)) ** 2 for k, v in b.items())) + 1e-9 for b in Ca])
    return S / na[:, None] / nb[None, :]
def metr(S):
    order = np.argsort(-S, 1, kind='stable'); rank = np.array([np.where(order[i] == i)[0][0] + 1 for i in range(len(S))])
    return dict(r1=float((rank == 1).mean()), r10=float((rank <= 10).mean()), mrr=float((1 / rank).mean()))
res = {}
for name, jk, ck in CONDS:
    r = {}
    for mname, kv in (('w2v-firefox', FF), ('w2v-GoogleNews', GN)):
        for wt in (False, True):
            J = np.stack([bag(t, kv, wt) for t in T[jk]]); C = np.stack([bag(t, kv, wt) for t in T[ck]])
            r[f'{mname}{" idf" if wt else ""}'] = metr(J @ C.T)
            if mname == 'w2v-firefox' and wt and name == 'C0 raw':
                # language offset (halves)
                A = np.arange(n) % 2 == 0; B = ~A; out = []
                for tr, te in ((A, B), (B, A)):
                    off = C[tr].mean(0) - J[tr].mean(0); Jt = J[te] + off; Jt /= np.linalg.norm(Jt, axis=1, keepdims=True)
                    out.append((metr(J[te] @ C[te].T)['mrr'], metr(Jt @ C[te].T)['mrr']))
                r['offset_halfpool_mrr(no,with)'] = [float(np.mean([o[0] for o in out])), float(np.mean([o[1] for o in out]))]
    Ja, Ca = tfidf_mat(T[jk]), tfidf_mat(T[ck]); r['tfidf-words (symbolic)'] = metr(sparse_sim(Ja, Ca))
    res[name] = r
# decoy and mismatch: JS with a different method name; does word2vec follow the name (decoy) or the rest of the body?
r = {}
for mname, kv in (('w2v-firefox idf', FF), ('w2v-GoogleNews idf', GN)):
    J = np.stack([bag(t, kv, True) for t in T['js_decoy']]); C = np.stack([bag(t, kv, True) for t in T['cpp_raw']]); top = (J @ C.T).argmax(1)
    r[mname] = dict(top1_is_original=float((top == np.arange(n)).mean()), top1_is_decoy_cpp=float((top == decoy).mean()))
res['C8 decoy name in JS'] = r
# similarity of method-name words across languages (what word2vec adds over exact match): cosine of lower-first vs capitalized names, and of related words
json.dump(res, open('w2v_results.json', 'w'), indent=1)
for k, v in res.items():
    print(k)
    for m, x in v.items(): print('   %-26s %s' % (m, {a: (round(b, 2) if isinstance(b, float) else [round(c, 2) for c in b]) for a, b in x.items()} if isinstance(x, dict) else [round(c, 2) for c in x]))
