"""Section 23's C++<->JS link test, routed through the exact index: name -> interface -> implementing classes -> rank by embedding."""
import json, re, numpy as np, torch, os
from tree_sitter import Language, Parser
import tree_sitter_cpp
from transformers import AutoTokenizer, AutoModel
torch.set_num_threads(4)
R = '/home/user/mozilla/gecko-dev'; CPP = Parser(Language(tree_sitter_cpp.language()))
I = json.load(open('index2.json')); iface = I['interfaces']; decl = I['methods']; impls = I['impls']
V = json.load(open('variants.json')); P = V['pairs']; n = len(P)
E = np.load('emb_qwen3.npz'); Jraw, Craw, Jmask = E['js_raw'], E['cpp_raw'], E['js_indep']
def fn_at(path, line):
    src = open(os.path.join(R, path), 'rb').read(); t = CPP.parse(src); st = [t.root_node]
    while st:
        x = st.pop()
        if x.type == 'function_definition' and x.start_point[0] + 1 == line: return src[x.start_byte:x.end_byte].decode('utf8', 'ignore')
        if x.start_point[0] + 1 <= line <= x.end_point[0] + 1: st.extend(x.children)
    return None
cands = []   # per pair: list of dict(cls,file,line,code)
for p in P:
    nm = p['name']; lst = []
    for i in decl.get(nm, []):
        for x in impls.get(i, {}).get(nm, []):
            lst.append(dict(cls=x['cls'], file=x['file'], line=x['line']))
    seen = set(); uniq = []
    for x in lst:
        k = (x['cls'], x['file'], x['line'])
        if k not in seen: seen.add(k); uniq.append(x)
    cands.append(uniq)
need = [(i, j) for i, c in enumerate(cands) for j, x in enumerate(c)]
for i, j in need: cands[i][j]['code'] = fn_at(cands[i][j]['file'], cands[i][j]['line'])
texts = [(i, j, cands[i][j]['code']) for i, j in need if cands[i][j]['code']]
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B', padding_side='left'); m = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', dtype=torch.float32).eval()
Z = []
for k in range(0, len(texts), 8):
    b = tok([t[2] for t in texts[k:k + 8]], padding=True, truncation=True, max_length=256, return_tensors='pt')
    with torch.no_grad(): Z.append(torch.nn.functional.normalize(m(**b).last_hidden_state[:, -1], dim=1).numpy())
Z = np.vstack(Z)
for (i, j, _), z in zip(texts, Z): cands[i][j]['z'] = z
size, found, hit_q, hit_rand, hit_q_mask = [], [], [], [], []
for i, p in enumerate(P):
    cs = [c for c in cands[i] if 'z' in c]; size.append(len(cs))
    true = [k for k, c in enumerate(cs) if c['cls'] == p['cpp_cls'] and c['file'] == p['cpp_file']]
    found.append(bool(true))
    if not true: hit_q.append(0.0); hit_rand.append(0.0); continue
    s = np.array([Jraw[i] @ c['z'] for c in cs]); hit_q.append(float(np.argmax(s) == true[0])); hit_rand.append(1 / len(cs))
size = np.array(size); found = np.array(found); hit_q = np.array(hit_q); hit_rand = np.array(hit_rand)
# global pool baselines from section 23
S = Jraw @ Craw.T; r1_global = float((S.argmax(1) == np.arange(n)).mean()); Sm = Jmask @ Craw.T; r1_masked = float((Sm.argmax(1) == np.arange(n)).mean())
print('pairs', n, '| pairs whose true implementation is in the index candidate set: %.2f' % found.mean(), '| candidate-set size median %d mean %.1f max %d' % (np.median(size), size.mean(), size.max()))
print('exact route, rank inside the set by Qwen3: R@1 %.2f  (random inside the set %.2f)  | global 129-way Qwen3 R@1 %.2f' % (hit_q.mean(), hit_rand.mean(), r1_global))
print('by set size: ', {k: (int(((size == k) if k < 4 else (size >= 4)).sum()), round(float(hit_q[(size == k) if k < 4 else (size >= 4)].mean()), 2), round(float(hit_rand[(size == k) if k < 4 else (size >= 4)].mean()), 2)) for k in (1, 2, 3, 4)}, '(n, Qwen3, random)')
print('JS method name masked: the exact route is unavailable; fallback to global pool R@1 %.2f' % r1_masked)
json.dump(dict(pairs=n, in_set=float(found.mean()), set_size_mean=float(size.mean()), r1_route=float(hit_q.mean()), r1_random_in_set=float(hit_rand.mean()), r1_global=r1_global, r1_global_name_masked=r1_masked), open('link_through_index.json', 'w'), indent=1)
