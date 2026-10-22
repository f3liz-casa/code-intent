"""Index v2: + IDL attributes, contract IDs (components.conf), JS receiver typing (getService / defineLazyServiceGetter / Services.x / QueryInterface)."""
import os, re, json, ast, collections
I = json.load(open('index3_base.json')); iface = I['interfaces']; decl = I['methods']; cls_if = {c: set(v) for c, v in I['class_interfaces'].items()}
R = '/home/user/mozilla/gecko-dev'
low = lambda n: n[0].lower() + n[1:]; cap = lambda n: n[0].upper() + n[1:]
def chain(i):
    out = []
    while i in iface and i not in out: out.append(i); i = iface[i]['base']
    return out
# ---- 1. attributes from IDL
attrs = collections.defaultdict(dict)    # interface -> {name: readonly}
for n, d in iface.items():
    txt = open(os.path.join(R, d['file']), errors='ignore').read(); txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S); txt = re.sub(r'//.*', '', txt)
    m = re.search(r'interface\s+%s\b[^{]*\{(.*?)\n\};' % re.escape(n), txt, flags=re.S)
    if not m: continue
    for a in re.finditer(r'(readonly\s+)?attribute\s+[\w:<>\s\*]+?\b(\w+)\s*;', m.group(1)):
        attrs[n][a.group(2)] = bool(a.group(1))
print('interfaces with attributes', len(attrs), 'attributes', sum(len(v) for v in attrs.values()), flush=True)
# ---- 2. C++ method defs again (for GetFoo/SetFoo)
from tree_sitter import Language, Parser
import tree_sitter_cpp
CPP = Parser(Language(tree_sitter_cpp.language()))
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
defs = collections.defaultdict(list)
for dp, _, fs in os.walk(R):
    if '/.git' in dp: continue
    for f in fs:
        if not f.endswith(('.cpp', '.cc')): continue
        p = os.path.join(dp, f); src = open(p, 'rb').read()
        if len(src) > 600_000: continue
        for n in walk(CPP.parse(src).root_node):
            if n.type != 'function_definition': continue
            d = n.child_by_field_name('declarator')
            if d is None: continue
            m = re.search(r'(\w+)::(\w+)\s*\(', src[d.start_byte:d.end_byte].decode('utf8', 'ignore'))
            if m: defs[(m.group(1), low(m.group(2)))].append(dict(file=os.path.relpath(p, R), line=n.start_point[0] + 1))
attr_impl = collections.defaultdict(lambda: collections.defaultdict(list))   # iface -> attr -> [impl]
for c, ifs in cls_if.items():
    for i in ifs:
        for anc in chain(i):
            for a in attrs.get(anc, {}):
                for acc in ('get' + cap(a), 'set' + cap(a)):
                    for l in defs.get((c, acc), []): attr_impl[anc][a].append(dict(cls=c, accessor=acc, **l))
print('attributes with a C++ accessor implementation', sum(len(v) for v in attr_impl.values()), flush=True)
# ---- 3. contract IDs from components.conf
import subprocess
confs = {p: open(os.path.join(R, p), errors='ignore').read() for p in subprocess.run(['git', '-C', R, 'ls-files'], capture_output=True, text=True).stdout.split('\n') if p.endswith('components.conf')}; contracts = {}
for path, txt in confs.items():
    m = re.search(r'Classes\s*=\s*(\[.*\])', txt, flags=re.S)
    if not m: continue
    try: classes = ast.literal_eval(m.group(1))
    except Exception:
        try: classes = ast.literal_eval(re.sub(r'#.*', '', m.group(1)))
        except Exception: continue
    for c in classes:
        for cid in c.get('contract_ids', []) or []:
            contracts[cid] = dict(interfaces=c.get('interfaces', []), cpp_class=c.get('type'), js_module=c.get('esModule') or c.get('jsm'), js_ctor=c.get('constructor'), conf=path)
# derive interfaces for contracts without `interfaces` from the C++ class map
for cid, c in contracts.items():
    if not c['interfaces'] and c['cpp_class']: c['interfaces'] = sorted(cls_if.get(c['cpp_class'].split('::')[-1], []))
print('contract ids', len(contracts), 'with interfaces', sum(bool(c['interfaces']) for c in contracts.values()), flush=True)
svc = {v: k for k, v in json.load(open('conf/services.json')).items()}     # Services.<name> -> interface
# ---- 4. JS typing + call-site resolution
sites = [json.loads(l) for l in open('js_sites3.jsonl')]
files = sorted({s['file'] for s in sites}); typed = {}
pat_lazy = re.compile(r'defineLazyServiceGetter\(\s*[\w.]+\s*,\s*["\'](\w+)["\']\s*,\s*["\'](@[^"\']+)["\']\s*(?:,\s*["\'](nsI\w+|moz\w+)["\'])?')
pat_get = re.compile(r'(?:const|let|var)?\s*(\w+)\s*=\s*Cc\[\s*["\'](@[^"\']+)["\']\s*\]\s*\.(?:getService|createInstance)\(\s*(?:Ci\.(nsI\w+))?\s*\)')
pat_qi = re.compile(r'(?:const|let|var)?\s*(\w+)\s*=\s*[\w.]+\.QueryInterface\(\s*Ci\.(nsI\w+)\s*\)')
for f in files:
    txt = open(os.path.join(R, f), errors='ignore').read(); t = {}
    for m in pat_lazy.finditer(txt):
        name, cid, i = m.groups(); i = i or (contracts.get(cid, {}).get('interfaces') or [None])[0]
        if i: t[name] = i
    for m in pat_get.finditer(txt):
        name, cid, i = m.groups(); i = i or (contracts.get(cid, {}).get('interfaces') or [None])[0]
        if i: t[name] = i
    for m in pat_qi.finditer(txt): t[m.group(1)] = m.group(2)
    typed[f] = t
def type_of(s):
    r = s['recv']; r = re.sub(r'^(this|lazy)\.', '', r)
    if r.startswith('Services.'): return svc.get(r.split('.', 1)[1].split('.')[0]) if False else {v: k for k, v in svc.items()}.get(r.split('.')[1]) if len(r.split('.')) > 1 else None
    return typed[s['file']].get(r)
name2iface = json.load(open('conf/services.json'))   # interface -> Services.<name>
svc_name = {v: k for k, v in name2iface.items()}
def type_of(s):
    r = re.sub(r'^(this|lazy)\.', '', s['recv'])
    if r.startswith('Services.'):
        parts = r.split('.'); return svc_name.get(parts[1]) if len(parts) > 1 else None
    return typed[s['file']].get(r)
res = dict(total=0, typed=0, amb=0, amb_typed=0, agree=0, both=0, declared=0)
out = []
for s in sites:
    res['total'] += 1; ty = type_of(s); cands = decl[s['method']]; amb = len(cands) > 1; res['amb'] += amb
    if not ty: continue
    res['typed'] += 1; res['amb_typed'] += amb
    d = next((a for a in chain(ty) if s['method'] in iface[a]['methods']), None)
    if d: res['declared'] += 1
    s['typed_iface'] = ty; s['typed_decl'] = d
    truth = [c for c in cands if any(c in chain(h) for h in s['hints'] if h in iface)]
    if d and len(truth) == 1: res['both'] += 1; res['agree'] += (d == truth[0])
    out.append(dict(file=s['file'], line=s['line'], method=s['method'], recv=s['recv'], typed=ty, decl=d, hints=s['hints']))
print(res, flush=True)

# ---- 5. JS and Rust implementers (impls3.json)
other = json.load(open('impls3.json')); n_if = collections.Counter()
for im in other:
    for i in im['interfaces']:
        for anc in chain(i):
            names = set(iface[anc]['methods']) | set(attrs.get(anc, {}))
            for m in im['methods']:
                mm = m[0].lower() + m[1:] if im['lang'] == 'rust' else m
                mm2 = re.sub(r'^(get|set)([A-Z])', lambda x: x.group(2).lower(), mm)
                hit = mm if mm in iface[anc]['methods'] else (mm2 if mm2 in attrs.get(anc, {}) else None)
                if hit:
                    I.setdefault('impls_other', {}).setdefault(anc, {}).setdefault(hit, []).append(dict(cls=im['cls'], lang=im['lang'], file=im['file'], line=im['line'], test=im['test'], via=i)); n_if[im['lang']] += 1
print('(iface, member) implementations in JS/Rust', dict(n_if), flush=True)
I['other_impls'] = other
I['attributes'] = {i: v for i, v in attrs.items()}; I['attribute_impls'] = {i: dict(v) for i, v in attr_impl.items()}; I['contracts'] = contracts
json.dump(I, open('index3.json', 'w')); json.dump(out, open('typed_sites3.json', 'w')); json.dump(res, open('index3_stats.json', 'w'))
