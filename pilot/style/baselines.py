"""Non-neural baselines for style identification (leave-one-intent-out): length only, and bag of tokens on hashed code."""
import json, re, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
D = json.load(open('texts.json')); ds = [x for x in D['items'] if x['kind'] == 'dataset']
intent = np.array([x['intent'] for x in ds]); style = np.array([x['style'] for x in ds]); I = sorted(set(intent))
def loio(X):
    acc = []
    for i in I:
        tr = intent != i
        clf = LogisticRegression(max_iter=3000, C=10).fit(X[tr], style[tr]); acc.append((clf.predict(X[~tr]) == style[~tr]).mean())
    return round(float(np.mean(acc)), 2)
for var in ['raw', 'hashed']:
    txt = [x[var] for x in ds]
    L = np.array([[t.count('\n') + 1, len(t), len(re.findall(r'\w+', t))] for t in txt], float); L = (L - L.mean(0)) / L.std(0)
    tf = TfidfVectorizer(token_pattern=r'[A-Za-z_]\w*|[^\sA-Za-z_0-9]', lowercase=False, min_df=2).fit_transform(txt).toarray()
    # keyword-only tokens (drop identifiers) so no name leakage at all
    import keyword
    kw = set(keyword.kwlist) | {'np', 'numpy', 'self', 'lambda', 'reduce', 'map', 'filter', 'class', 'sorted', 'sum'}
    k_only = [' '.join(t for t in re.findall(r'[A-Za-z_]\w*|[^\sA-Za-z_0-9]', s) if t in kw or not re.match(r'[A-Za-z_]', t)) for s in txt]
    kf = TfidfVectorizer(token_pattern=r'\S+', lowercase=False, min_df=2).fit_transform(k_only).toarray()
    print(var, 'length-only', loio(L), '| token tf-idf', loio(tf), '| keyword+punct tf-idf', loio(kf), '(chance 0.20)')
