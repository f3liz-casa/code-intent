"""Extract XPCOM-linked pairs: IDL method names -> C++ implementations (nsFoo::MethodName) and JS functions that call .methodName(...)."""
import os, re, json, sys, collections, random
from tree_sitter import Language, Parser
import tree_sitter_cpp, tree_sitter_javascript
R = '/home/user/mozilla/gecko-dev'
CPP = Parser(Language(tree_sitter_cpp.language())); JS = Parser(Language(tree_sitter_javascript.language()))
random.seed(0)
# ---- 1. IDL methods
idl_methods = collections.defaultdict(set)   # method name -> {interface}
for dp, _, fs in os.walk(R):
    for f in fs:
        if not f.endswith('.idl'): continue
        txt = open(os.path.join(dp, f), errors='ignore').read()
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S); txt = re.sub(r'//.*', '', txt)
        for im in re.finditer(r'interface\s+(\w+)[^{;]*\{(.*?)\n\};', txt, flags=re.S):
            iface, body = im.group(1), im.group(2)
            for ln in body.split(';'):
                ln = ' '.join(ln.split())
                if 'attribute' in ln or ln.startswith(('const', 'typedef', 'cenum')) or '(' not in ln: continue
                m = re.search(r'(\w+)\s*\(', re.sub(r'\[[^\]]*\]', '', ln))
                if m and not m.group(1).startswith('_'): idl_methods[m.group(1)].add(iface)
print('idl methods', len(idl_methods), flush=True)
cap = lambda n: n[0].upper() + n[1:]
unique = {n: next(iter(i)) for n, i in idl_methods.items() if len(i) == 1 and len(n) >= 8 and re.search(r'[a-z][A-Z]', n)}   # multiword camelCase, one interface
print('unique multiword', len(unique), flush=True)
# ---- 2. C++ implementations
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
cpp = collections.defaultdict(list)
for dp, _, fs in os.walk(R):
    for f in fs:
        if not f.endswith(('.cpp', '.cc')): continue
        p = os.path.join(dp, f); src = open(p, 'rb').read()
        if len(src) > 600_000: continue
        t = CPP.parse(src)
        for n in walk(t.root_node):
            if n.type != 'function_definition': continue
            d = n.child_by_field_name('declarator')
            if d is None: continue
            txt = src[d.start_byte:d.end_byte].decode('utf8', 'ignore')
            m = re.search(r'(\w+)::(\w+)\s*\(', txt)
            if not m: continue
            cls, name = m.group(1), m.group(2)
            low = name[0].lower() + name[1:]
            if low in unique and cls.startswith(('ns', 'mozilla', 'Ns', 'Moz')) or (low in unique and '::' in txt):
                code = src[n.start_byte:n.end_byte].decode('utf8', 'ignore'); nl = code.count('\n') + 1
                if 5 <= nl <= 80: cpp[low].append(dict(name=low, cls=cls, file=os.path.relpath(p, R), code=code))
print('cpp impls for', len(cpp), 'names', sum(len(v) for v in cpp.values()), flush=True)
# ---- 3. JS functions that call .name(
FN = {'function_declaration', 'function_expression', 'method_definition', 'arrow_function', 'generator_function_declaration', 'function'}
js = collections.defaultdict(list)
for dp, _, fs in os.walk(R):
    for f in fs:
        if not f.endswith(('.js', '.mjs', '.jsm')): continue
        p = os.path.join(dp, f); src = open(p, 'rb').read()
        if len(src) > 600_000: continue
        t = JS.parse(src)
        for n in walk(t.root_node):
            if n.type not in FN: continue
            code = src[n.start_byte:n.end_byte].decode('utf8', 'ignore'); nl = code.count('\n') + 1
            if not (5 <= nl <= 60): continue
            names = {m for m in re.findall(r'\.(\w+)\s*\(', code) if m in unique and m in cpp}
            if len(names) != 1: continue
            # innermost only: skip if a nested function also contains the call
            nm = next(iter(names)); js[nm].append(dict(name=nm, file=os.path.relpath(p, R), code=code))
print('js callers for', len(js), 'names', sum(len(v) for v in js.values()), flush=True)
names = sorted(set(cpp) & set(js)); pairs = []
for nm in names:
    c = cpp[nm][0]; nt = [j for j in js[nm] if 'test' not in j['file'].lower()]; jj = random.choice(nt or js[nm])
    pairs.append(dict(name=nm, iface=unique[nm], cpp=c['code'], cpp_cls=c['cls'], cpp_file=c['file'], js=jj['code'], js_file=jj['file'], js_is_test=('test' in jj['file'].lower()), n_cpp=len(cpp[nm]), n_js=len(js[nm])))
json.dump(pairs, open('pairs.json', 'w'))
print('pairs', len(pairs)); print([p['name'] for p in pairs[:15]])
