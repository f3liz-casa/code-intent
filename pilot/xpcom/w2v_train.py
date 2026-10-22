import json, time
from gensim.models import Word2Vec
S = json.load(open('w2v_sentences.json')); t = time.time()
m = Word2Vec(S, vector_size=100, window=8, min_count=3, sg=1, negative=10, epochs=15, workers=4, seed=1)
m.save('w2v_firefox.model'); print('trained', len(m.wv), 'words in %.0fs' % (time.time() - t))
for w in ['channel', 'request', 'cookie', 'async', 'listener', 'cache', 'nsresult', 'await', 'promise']:
    if w in m.wv: print(w, [x for x, _ in m.wv.most_similar(w, topn=6)])
