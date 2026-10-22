import json, re, random, hashlib
random.seed(1)
P = [p for p in json.load(open('pairs.json')) if not p['js_is_test']]; random.shuffle(P)   # JS callers from application code (non-test paths)
KW = set('''alignas alignof and auto bool break case catch char class const constexpr continue decltype default delete do double else enum explicit extern false float for friend goto if inline int long mutable namespace new nullptr operator private protected public register return short signed sizeof static struct switch template this throw true try typedef typename union unsigned using virtual void volatile while
async await const debugger export extends finally function get import in instanceof let null of set super typeof undefined var yield from as of arguments NS_IMETHODIMP NS_OK nsresult Services Ci Cc Cu Cr XPCOMUtils console'''.split())
def h(tok, salt=''): return 'v' + hashlib.md5((salt + tok).encode()).hexdigest()[:6]
def mask_name(code, n, rep):
    N = n[0].upper() + n[1:]; return re.sub(r'\b(%s|%s)\b' % (re.escape(n), re.escape(N)), rep, code)
def hash_all(code, salt=''):
    return re.sub(r'\b[A-Za-z_]\w*\b', lambda m: m.group(0) if m.group(0) in KW else h(m.group(0), salt), code)
names = [p['name'] for p in P]
T = {k: [] for k in ['cpp_raw', 'cpp_same', 'cpp_indep', 'cpp_allcons', 'cpp_allsalt', 'js_raw', 'js_same', 'js_indep', 'js_decoy', 'js_allcons', 'js_allsalt', 'cpp_name', 'js_name']}
for i, p in enumerate(P):
    n = p['name']; N = n[0].upper() + n[1:]; hs = h(n, 'link'); decoy = names[(i + 37) % len(names)]
    T['cpp_raw'].append(p['cpp']); T['js_raw'].append(p['js'])
    T['cpp_same'].append(mask_name(p['cpp'], n, hs)); T['js_same'].append(mask_name(p['js'], n, hs))
    T['cpp_indep'].append(mask_name(p['cpp'], n, h(n, 'c'))); T['js_indep'].append(mask_name(p['js'], n, h(n, 'j')))
    T['js_decoy'].append(mask_name(p['js'], n, decoy))
    T['cpp_allcons'].append(hash_all(p['cpp'])); T['js_allcons'].append(hash_all(p['js']))
    T['cpp_allsalt'].append(hash_all(p['cpp'], 'c')); T['js_allsalt'].append(hash_all(p['js'], 'j'))
    T['cpp_name'].append(N); T['js_name'].append(n)
json.dump(dict(pairs=P, texts=T, decoy_index=[(i + 37) % len(P) for i in range(len(P))]), open('variants.json', 'w'))
print(len(P), {k: len(v) for k, v in T.items()}); print(T['js_decoy'][0][:300]); print(T['cpp_allcons'][0][:200])
