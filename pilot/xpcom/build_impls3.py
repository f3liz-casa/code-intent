"""JS and Rust XPCOM implementers on the full tree: class/object -> interfaces (generateQI / #[xpcom(implement(..))]) -> method names defined."""
import os, re, json, collections, subprocess
from tree_sitter import Language, Parser
import tree_sitter_javascript
R = '/home/user/mozilla/gecko-dev'
JS = Parser(Language(tree_sitter_javascript.language()))
files = subprocess.run(['git', '-C', R, 'ls-files'], capture_output=True, text=True).stdout.split('\n')
is_test = lambda p: bool(re.search(r'(^|/)(test|tests|gtest|testing|browser/.*/test|mochitest|xpcshell)(/|$)|test_|_test\.', p))
def txt(src, n): return src[n.start_byte:n.end_byte].decode('utf8', 'ignore')
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
# ---------- JS
js_impls = []
for p in files:
    if not p.endswith(('.js', '.mjs', '.sys.mjs', '.jsm')): continue
    full = os.path.join(R, p)
    try: src = open(full, 'rb').read()
    except OSError: continue
    if b'generateQI' not in src or len(src) > 800_000: continue
    t = JS.parse(src)
    for n in walk(t.root_node):
        if n.type != 'call_expression': continue
        f = n.child_by_field_name('function')
        if f is None or not txt(src, f).endswith('generateQI'): continue
        ifs = re.findall(r'nsI[A-Z]\w+|mozI\w+', txt(src, n))
        if not ifs: continue
        # owner: nearest class body or object literal, else enclosing named variable
        o = n.parent; owner = None
        while o is not None:
            if o.type in ('class_body', 'object'): owner = o; break
            o = o.parent
        if owner is None: continue
        holder = owner.parent; name = None
        if holder is not None and holder.type in ('class_declaration', 'class'):
            nm = holder.child_by_field_name('name'); name = txt(src, nm) if nm else None
            if name is None and holder.parent is not None and holder.parent.type == 'variable_declarator':
                name = txt(src, holder.parent.child_by_field_name('name'))
        elif holder is not None and holder.type == 'variable_declarator':
            name = txt(src, holder.child_by_field_name('name'))
        elif holder is not None and holder.type == 'pair':
            name = txt(src, holder.child_by_field_name('key'))
        elif holder is not None and holder.type in ('assignment_expression',):
            name = txt(src, holder.child_by_field_name('left')).split('.')[-1]
        if not name: name = '<anon@%s:%d>' % (os.path.basename(p), owner.start_point[0] + 1)
        methods = set()
        for c in owner.children:
            if c.type in ('method_definition',):
                k = c.child_by_field_name('name'); methods.add(txt(src, k))
            elif c.type == 'pair':
                v = c.child_by_field_name('value')
                if v is not None and v.type in ('function_expression', 'arrow_function', 'function'): methods.add(txt(src, c.child_by_field_name('key')))
        js_impls.append(dict(lang='js', cls=name, file=p, line=owner.start_point[0] + 1, interfaces=sorted(set(ifs)), methods=sorted(methods), test=is_test(p)))
print('JS implementers', len(js_impls), 'non-test', sum(not i['test'] for i in js_impls), flush=True)
# ---------- Rust
rs_impls = []
pat_attr = re.compile(r'#\[xpcom\(\s*(?:\w+\s*,\s*)*implement\(([^)]*)\)[^\]]*\]\s*(?:#\[[^\]]*\]\s*)*(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)')
for p in files:
    if not p.endswith('.rs'): continue
    try: s = open(os.path.join(R, p), errors='ignore').read()
    except OSError: continue
    if '#[xpcom(' not in s: continue
    for m in pat_attr.finditer(s):
        ifs = re.findall(r'nsI\w+|mozI\w+', m.group(1)); cls = m.group(2); methods = set()
        for im in re.finditer(r'impl(?:<[^>]*>)?\s+%s(?:<[^>]*>)?\s*\{' % re.escape(cls), s):
            depth = 1; i = im.end()
            while i < len(s) and depth:
                depth += (s[i] == '{') - (s[i] == '}'); i += 1
            body = s[im.end():i]
            methods |= set(re.findall(r'xpcom_method!\(\s*\w+\s*=>\s*(\w+)', body)); methods |= set(re.findall(r'(?:unsafe\s+)?fn\s+([A-Z]\w+)\s*\(', body))
        rs_impls.append(dict(lang='rust', cls=cls, file=p, line=s[:m.start()].count('\n') + 1, interfaces=sorted(set(ifs)), methods=sorted(methods), test=is_test(p)))
print('Rust implementers', len(rs_impls), 'with methods', sum(bool(i['methods']) for i in rs_impls), flush=True)
json.dump(js_impls + rs_impls, open('impls3.json', 'w'))
