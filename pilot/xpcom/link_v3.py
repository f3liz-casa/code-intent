"""Link test on the full tree with C++/JS/Rust implementers: JS caller (typed receiver, non-test) <-> implementer code.
A: unique-implementer pairs (clean pair set from the index): global Qwen3 retrieval, name unmasked / masked, by implementer language.
B: multi-implementer sets with contract-ID truth: does the contract pick the class, and does the embedding?"""
import json, re, os, random, collections, numpy as np, torch
from tree_sitter import Language, Parser
import tree_sitter_cpp, tree_sitter_javascript
from transformers import AutoTokenizer, AutoModel
torch.set_num_threads(4); random.seed(0)
R = '/home/user/mozilla/gecko-dev'; CPP = Parser(Language(tree_sitter_cpp.language())); JS = Parser(Language(tree_sitter_javascript.language()))
I = json.load(open('index3.json')); T = json.load(open('typed_sites3.json')); cpp = I['impls']; oth = I.get('impls_other', {}); contracts = I['contracts']
is_test = lambda p: bool(re.search(r'(^|/)(test|tests|gtest|testing|mochitest|xpcshell|browser/.*/test)(/|$)|(^|/)(test_|head_)|_test\.|third_party|/tools/', p))
sites = {}
for l in open('js_sites3.jsonl'):
    s = json.loads(l); sites[(s['file'], s['line'], s['method'])] = s
def cands(t):
    d, m = t['decl'], t['method']; out = {}
    for x in cpp.get(d, {}).get(m, []): out[('cpp', x['cls'], x['file'], x['line'])] = 1
    for x in oth.get(d, {}).get(m, []):
        if not x['test']: out[(x['lang'], x['cls'], x['file'], x['line'])] = 1
    return list(out)
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
def body(c, m):
    lang, cls, f, line = c; src = open(os.path.join(R, f), 'rb').read()
    if lang == 'cpp':
        t = CPP.parse(src); st = [t.root_node]
        while st:
            x = st.pop()
            if x.type == 'function_definition' and x.start_point[0] + 1 == line: return src[x.start_byte:x.end_byte].decode('utf8', 'ignore')
            if x.start_point[0] + 1 <= line <= x.end_point[0] + 1: st.extend(x.children)
        return None
    if lang == 'js':
        t = JS.parse(src)
        for n in walk(t.root_node):
            if n.type in ('class_body', 'object') and n.start_point[0] + 1 == line:
                for c2 in n.children:
                    k = c2.child_by_field_name('name') or c2.child_by_field_name('key')
                    if c2.type in ('method_definition', 'pair') and k is not None and src[k.start_byte:k.end_byte].decode() in (m, re.sub(r'^(get|set)([A-Z])', lambda y: y.group(2).lower(), m)):
                        return src[c2.start_byte:c2.end_byte].decode('utf8', 'ignore')
        return None
    s = src.decode('utf8', 'ignore'); mm = re.search(r'xpcom_method!\(\s*(\w+)\s*=>\s*%s\b' % re.escape(m[0].upper() + m[1:]), s)
    fn = mm.group(1) if mm else m[0].upper() + m[1:]
    mm = re.search(r'fn\s+%s\s*\(' % re.escape(fn), s)
    if not mm: return None
    i = s.find('{', mm.end()); d = 1; j = i + 1
    while j < len(s) and d: d += (s[j] == '{') - (s[j] == '}'); j += 1
    return s[mm.start():j]
# ---- A: unique implementer
nt = [t for t in T if t['decl'] and not is_test(t['file'])]
A = collections.defaultdict(list); B = []
for t in nt:
    cs = cands(t)
    if len(cs) == 1: A[cs[0][0]].append((t, cs[0]))
    elif 2 <= len(cs) <= 6: B.append((t, cs))
quota = {'cpp': 150, 'js': 100, 'rust': 50}; pairs = []
for lang, lst in A.items():
    random.shuffle(lst); seen = set()
    for t, c in lst:
        if len(seen) >= quota[lang]: break
        if c in seen or (t['file'], t['line'], t['method']) not in sites: continue
        jc = sites[(t['file'], t['line'], t['method'])]['code']; ic = body(c, t['method'])
        if not ic or len(ic) < 40: continue
        seen.add(c); pairs.append(dict(lang=lang, method=t['method'], js=jc, impl=ic, cls=c[1], file=c[2]))
print('A pairs', collections.Counter(p['lang'] for p in pairs), 'unique-impl sites available', {k: len(v) for k, v in A.items()}, flush=True)
def mask(s, m): return re.sub(re.escape(m), 'XXXX', re.sub(re.escape(m[0].upper() + m[1:]), 'XXXX', s), flags=re.I)
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B', padding_side='left'); mod = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', dtype=torch.float32).eval()
def emb(texts):
    Z = []
    for k in range(0, len(texts), 8):
        b = tok(texts[k:k + 8], padding=True, truncation=True, max_length=256, return_tensors='pt')
        with torch.no_grad(): Z.append(torch.nn.functional.normalize(mod(**b).last_hidden_state[:, -1], dim=1).numpy())
    return np.vstack(Z)
Jr = emb([p['js'] for p in pairs]); Ir = emb([p['impl'] for p in pairs])
Jm = emb([mask(p['js'], p['method']) for p in pairs]); Im = emb([mask(p['impl'], p['method']) for p in pairs])
lang = np.array([p['lang'] for p in pairs]); n = len(pairs)
def r1(Jx, Ix, pool=None):
    S = Jx @ Ix.T; return (S.argmax(1) == np.arange(n))
res = dict(A_n=n, A_langs=dict(collections.Counter(lang)))
for nm, hit in (('raw', r1(Jr, Ir)), ('name_masked', r1(Jm, Im))):
    res['A_' + nm] = float(hit.mean()); res['A_%s_by_lang' % nm] = {l: float(hit[lang == l].mean()) for l in set(lang)}
# same-language pool (candidate impls of the same language only) = a fairer pool for rust/js
for nm, (Jx, Ix) in (('raw', (Jr, Ir)), ('name_masked', (Jm, Im))):
    out = {}
    for l in set(lang):
        ix = np.where(lang == l)[0]; S = Jx[ix] @ Ix[ix].T; out[l] = float((S.argmax(1) == np.arange(len(ix))).mean())
    res['A_%s_samelang_pool' % nm] = out
res['A_random_chance_global'] = 1 / n
print(json.dumps(res, indent=1), flush=True)
# ---- C: multi sets with contract truth
pat_lazy = re.compile(r'defineLazyServiceGetter\(\s*[\w.]+\s*,\s*["\'](\w+)["\']\s*,\s*["\'](@[^"\']+)["\']')
pat_get = re.compile(r'(?:const|let|var)?\s*(\w+)\s*=\s*Cc\[\s*["\'](@[^"\']+)["\']\s*\]\s*\.(?:getService|createInstance)')
short = lambda c: (c or '').split('::')[-1]
fcache = {}; Cp = []
for t, cs in B:
    s = sites.get((t['file'], t['line'], t['method']))
    if not s: continue
    f = t['file']
    if f not in fcache:
        txt = open(os.path.join(R, f), errors='ignore').read(); d = {}
        for m in pat_lazy.finditer(txt): d[m.group(1)] = m.group(2)
        for m in pat_get.finditer(txt): d[m.group(1)] = m.group(2)
        fcache[f] = d
    r = re.sub(r'^(this|lazy)\.', '', s['recv']); cid = fcache[f].get(r)
    if not cid or cid not in contracts: continue
    c = contracts[cid]; names = {short(c['cpp_class']), c.get('js_ctor') or '', short(c.get('js_module'))} - {''}
    truth = [k for k, x in enumerate(cs) if x[1] in names]
    if len(truth) == 1: Cp.append((t, cs, truth[0], s))
print('C sets with contract truth', len(Cp), flush=True)
random.shuffle(Cp); Cp = Cp[:120]; hits = []; rnd = []; ok = 0
for t, cs, tr, s in Cp:
    codes = [body(c, t['method']) for c in cs]
    if any(c is None for c in codes): continue
    z = emb([s['code']] + codes); sc = z[1:] @ z[0]; hits.append(int(sc.argmax() == tr)); rnd.append(1 / len(cs))
res['C_n'] = len(hits); res['C_embed_R1'] = float(np.mean(hits)) if hits else None; res['C_random'] = float(np.mean(rnd)) if rnd else None
res['C_contract_total_with_truth'] = len(Cp)
print(json.dumps({k: v for k, v in res.items() if k.startswith('C_')}), flush=True)
json.dump(res, open('link_v3.json', 'w'), indent=1)
