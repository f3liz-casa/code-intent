"""Identifier-word sentences from every C++/JS function in the Firefox checkout (minus the evaluation pairs)."""
import os, re, json, sys
from tree_sitter import Language, Parser
import tree_sitter_cpp, tree_sitter_javascript
R = '/home/user/mozilla/gecko-dev'
CPP = Parser(Language(tree_sitter_cpp.language())); JS = Parser(Language(tree_sitter_javascript.language()))
excl = set()
for p in json.load(open('variants.json'))['pairs']: excl.add(p['cpp']); excl.add(p['js'])
def words(code):
    ids = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', code); out = []
    for i in ids:
        for part in re.split(r'_+', i):
            out += [w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+', part)]
    return [w for w in out if len(w) > 1]
FN_CPP = {'function_definition'}; FN_JS = {'function_declaration', 'function_expression', 'method_definition', 'arrow_function', 'generator_function_declaration'}
def walk(n):
    st = [n]
    while st:
        x = st.pop(); yield x; st.extend(reversed(x.children))
sent = []; n_cpp = n_js = 0
for dp, _, fs in os.walk(R):
    for f in fs:
        if f.endswith(('.cpp', '.cc')): P, kinds, lang = CPP, FN_CPP, 'c'
        elif f.endswith(('.js', '.mjs', '.jsm')): P, kinds, lang = JS, FN_JS, 'j'
        else: continue
        src = open(os.path.join(dp, f), 'rb').read()
        if len(src) > 600_000: continue
        t = P.parse(src)
        for n in walk(t.root_node):
            if n.type in kinds:
                code = src[n.start_byte:n.end_byte].decode('utf8', 'ignore')
                if code in excl or not (3 <= code.count('\n') + 1 <= 150): continue
                w = words(code)
                if len(w) >= 5: sent.append(w); n_cpp += lang == 'c'; n_js += lang == 'j'
json.dump(sent, open('w2v_sentences.json', 'w'))
print('sentences', len(sent), 'cpp', n_cpp, 'js', n_js, 'tokens', sum(map(len, sent)))
