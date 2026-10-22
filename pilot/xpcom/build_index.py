"""XPCOM bridge index: IDL method -> declaring interface -> C++ implementing classes (+ method definitions) -> JS call sites."""
import os, re, json, collections, hashlib, sys
from tree_sitter import Language, Parser
import tree_sitter_cpp, tree_sitter_javascript
R = '/home/user/mozilla/gecko-dev'
CPP = Parser(Language(tree_sitter_cpp.language())); JS = Parser(Language(tree_sitter_javascript.language()))
low = lambda n: n[0].lower() + n[1:]
files = collections.defaultdict(list)
for dp, _, fs in os.walk(R):
    if '/.git' in dp: continue
    for f in fs:
        ext = os.path.splitext(f)[1]; files[ext].append(os.path.join(dp, f))
rd = lambda p: open(p, errors='ignore').read()
# ---- 1. interfaces
iface = {}   # name -> dict(file, base, methods[], doc)
for p in files['.idl']:
    txt = rd(p); clean = re.sub(r'/\*(?!\*).*?\*/', '', txt, flags=re.S); clean = re.sub(r'(?m)^\s*//.*$', '', clean)
    for im in re.finditer(r'(/\*\*.*?\*/)?\s*(?:\[[^\]]*\]\s*)*interface\s+(\w+)\s*(?::\s*(\w+))?\s*\{(.*?)\n\};', clean, flags=re.S):
        doc, name, base, body = im.groups()
        methods = []
        for ln in re.sub(r'/\*.*?\*/', '', body, flags=re.S).split(';'):
            ln = ' '.join(ln.split())
            if 'attribute' in ln or ln.startswith(('const', 'typedef', 'cenum')) or '(' not in ln: continue
            m = re.search(r'(\w+)\s*\(', re.sub(r'\[[^\]]*\]', '', ln))
            if m and not m.group(1).startswith('_'): methods.append(m.group(1))
        iface[name] = dict(file=os.path.relpath(p, R), base=base, methods=methods, doc=' '.join(re.sub(r'[/*]+', ' ', doc or '').split())[:300])
def chain(i):
    out = []
    while i in iface and i not in out: out.append(i); i = iface[i]['base']
    return out
decl = collections.defaultdict(list)      # method -> [declaring interface]
for n, d in iface.items():
    for m in d['methods']: decl[m].append(n)
up = {n.upper(): n for n in iface}
print('interfaces', len(iface), 'methods', len(decl), 'ambiguous methods', sum(len(v) > 1 for v in decl.values()), flush=True)
# ---- 2. C++ classes -> interfaces
cls_if = collections.defaultdict(set); cls_files = collections.defaultdict(set)
pat_impl = re.compile(r'NS_IMPL_(?:CYCLE_COLLECTING_)?ISUPPORTS(?:_INHERITED)?\(\s*([\w:]+)\s*,([^)]*)\)')
pat_cls = re.compile(r'(?:^|\n)\s*(?:class|struct)\s+(?:\w+_API\s+)?(\w+)(?:\s+final)?\s*(?::([^{;]*))?\{')
for p in files['.h'] + files['.cpp']:
    txt = rd(p)
    for m in pat_impl.finditer(txt):
        c = m.group(1).split('::')[-1]
        for i in re.findall(r'nsI\w+', m.group(2)): cls_if[c].add(i)
    last = None
    for m in pat_cls.finditer(txt):
        c = m.group(1)
        for i in re.findall(r'\bnsI\w+', m.group(2) or ''): cls_if[c].add(i)
        # NS_DECL_NSIFOO macros inside this class body (up to the next class start or 4000 chars)
        seg = txt[m.end():m.end() + 4000]; nxt = pat_cls.search(seg); seg = seg[:nxt.start()] if nxt else seg
        for d in re.findall(r'NS_DECL_(NSI\w+)', seg):
            if d in up: cls_if[c].add(up[d])
        cls_files[c].add(os.path.relpath(p, R))
print('classes with interfaces', len(cls_if), flush=True)
# ---- 3. C++ method definitions
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
defs = collections.defaultdict(list)   # (class, lowerMethod) -> [loc]
for p in files['.cpp'] + files['.cc']:
    src = open(p, 'rb').read()
    if len(src) > 600_000: continue
    t = CPP.parse(src)
    for n in walk(t.root_node):
        if n.type != 'function_definition': continue
        d = n.child_by_field_name('declarator')
        if d is None: continue
        m = re.search(r'([\w:]*?)(\w+)::(\w+)\s*\(', src[d.start_byte:d.end_byte].decode('utf8', 'ignore'))
        if m: defs[(m.group(2), low(m.group(3)))].append(dict(file=os.path.relpath(p, R), line=n.start_point[0] + 1))
impls = collections.defaultdict(lambda: collections.defaultdict(list))   # declaring iface -> method -> [impl]
for (c, mth), locs in defs.items():
    for i in cls_if.get(c, ()):
        for anc in chain(i):
            if mth in iface[anc]['methods']:
                for l in locs: impls[anc][mth].append(dict(cls=c, via=i, **l))
n_impl_methods = sum(len(v) for v in impls.values()); print('(interface, method) pairs with a C++ implementation', n_impl_methods, flush=True)
# ---- 4. JS call sites (innermost function)
FN = {'function_declaration', 'function_expression', 'method_definition', 'arrow_function', 'generator_function_declaration'}
sites = []; names = set(decl)
for p in files['.js'] + files['.mjs'] + files['.jsm']:
    src = open(p, 'rb').read()
    if len(src) > 600_000: continue
    t = JS.parse(src); per = collections.defaultdict(lambda: collections.defaultdict(list))
    stack = [(t.root_node, None)]
    while stack:
        n, fn = stack.pop()
        if n.type in FN: fn = n
        if n.type == 'call_expression' and fn is not None:
            f = n.child_by_field_name('function')
            if f is not None and f.type == 'member_expression':
                prop = f.child_by_field_name('property'); obj = f.child_by_field_name('object')
                if prop is not None:
                    nm = src[prop.start_byte:prop.end_byte].decode('utf8', 'ignore')
                    if nm in names: per[fn.id][nm].append(src[obj.start_byte:obj.end_byte].decode('utf8', 'ignore')[:60] if obj is not None else '')
        for c in n.children: stack.append((c, fn))
    if not per: continue
    byid = {}
    for n in walk(t.root_node):
        if n.id in per: byid[n.id] = n
    for fid, calls in per.items():
        n = byid.get(fid)
        if n is None: continue
        code = src[n.start_byte:n.end_byte].decode('utf8', 'ignore'); nl = code.count('\n') + 1
        if not (3 <= nl <= 80): continue
        hints = sorted(set(re.findall(r'\bnsI[A-Z]\w+', code)))
        for nm, recvs in calls.items():
            sites.append(dict(file=os.path.relpath(p, R), line=n.start_point[0] + 1, method=nm, recv=recvs[0], hints=hints, code=code[:3000]))
print('JS call sites', len(sites), flush=True)
json.dump(dict(interfaces=iface, methods={k: v for k, v in decl.items()}, impls={i: dict(m) for i, m in impls.items()}, class_interfaces={c: sorted(v) for c, v in cls_if.items()}), open('index.json', 'w'))
with open('js_sites.jsonl', 'w') as f:
    for s in sites: f.write(json.dumps(s) + '\n')
# ---- stats
amb = {m for m, v in decl.items() if len(v) > 1}
covered = [s for s in sites if any(s['method'] in impls[i] for i in decl[s['method']] if i in impls)]
print('stats: sites on ambiguous names', sum(s['method'] in amb for s in sites), '| sites whose name has >=1 C++ impl', len(covered), 'of', len(sites))
