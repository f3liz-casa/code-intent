"""Language-agnostic unit extractor on tree-sitter: one JSON line per function / method with name-free structure counts and callee tokens.

usage: python3 extract_corpus.py <repo checkout> <repo name owner/repo> <out dir> [--max-units 20000] [--seed 0]

Writes <out>/<owner_repo>.units.jsonl.gz. The structure counts use the same meaning as the TypeScript extractor of sec. 27
(loops, array-style chains, property mutation, await/then, throw/try/switch/ternary, nesting depth, this/self use, being inside a class),
approximated from node-type names that differ by language (see FAMILIES). It is an approximation: a count of 0 can mean "not used" or
"this language has no such node"; the language is therefore an input of the model downstream.

Test, vendored, generated and docs paths are skipped. Units shorter than 3 lines are skipped. If a repository has more than
--max-units units, a seeded random sample is kept.
"""
import gzip, hashlib, json, os, random, re, sys
from tree_sitter_language_pack import get_parser

EXT = {'py': 'python', 'ts': 'typescript', 'tsx': 'tsx', 'js': 'javascript', 'mjs': 'javascript', 'jsx': 'javascript', 'java': 'java', 'kt': 'kotlin', 'cs': 'csharp',
       'c': 'c', 'cc': 'cpp', 'cpp': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp', 'go': 'go', 'rs': 'rust', 'php': 'php', 'rb': 'ruby', 'swift': 'swift',
       'pl': 'perl', 'pm': 'perl', 'scala': 'scala', 'ex': 'elixir', 'exs': 'elixir', 'hs': 'haskell'}
SKIP = re.compile(r'(^|/)(node_modules|vendor|third_party|thirdparty|3rdparty|external|deps|testdata|fixtures?|tests?|test|spec|__tests__|examples?|docs?|benchmarks?|generated|gen|dist|build|\.git)(/|$)|\.(min|pb|generated)\.|_test\.go$|\.d\.ts$|_generated|\.stories\.|_test\.(py|rs)$|test_[^/]*\.py$')

FUNC = {
    'python': {'function_definition'}, 'typescript': {'function_declaration', 'method_definition', 'arrow_function', 'function_expression', 'generator_function_declaration'},
    'tsx': None, 'javascript': None, 'java': {'method_declaration', 'constructor_declaration'}, 'kotlin': {'function_declaration'}, 'csharp': {'method_declaration', 'constructor_declaration', 'local_function_statement'},
    'c': {'function_definition'}, 'cpp': {'function_definition'}, 'go': {'function_declaration', 'method_declaration'}, 'rust': {'function_item'},
    'php': {'function_definition', 'method_declaration'}, 'ruby': {'method', 'singleton_method'}, 'swift': {'function_declaration', 'init_declaration'},
    'perl': {'subroutine_declaration_statement'}, 'scala': {'function_definition'}, 'elixir': set(), 'haskell': {'function'},
}
FUNC['tsx'] = FUNC['javascript'] = FUNC['typescript']
CLASS = re.compile(r'^(class|impl|interface|struct|trait|object|enum|record|protocol|extension|module_definition|class_specifier|struct_specifier|object_declaration|singleton_class)')
LOOP = re.compile(r'(for_statement|for_in_statement|for_of|foreach|while_statement|while_expression|do_statement|do_while|loop_expression|for_expression|for_range|enhanced_for|^for$|^while$|^until$|^repeat|for_clause|for_in_clause|until)')
IFS = {'if_statement', 'if_expression', 'if', 'elsif', 'unless', 'elif_clause', 'else_if_clause', 'if_modifier', 'unless_modifier', 'guard_statement', 'if_let_expression', 'guard'}
SWITCH = {'switch_statement', 'switch_expression', 'match_expression', 'match_statement', 'when_expression', 'case', 'case_match', 'expression_switch_statement', 'type_switch_statement', 'select_statement', 'case_statement', 'switch', 'case_expression'}
TRY = {'try_statement', 'try_expression', 'try', 'rescue', 'try_with_resources_statement', 'do_catch', 'begin'}
THROW = {'throw_statement', 'throw_expression', 'raise', 'raise_statement', 'throw', 'panic'}
TERN = {'ternary_expression', 'conditional_expression'}
AWAIT = {'await_expression', 'await'}
CATCH = {'catch_clause', 'except_clause', 'rescue_clause', 'catch_block', 'catch'}
CALL = {'call_expression', 'call', 'method_invocation', 'invocation_expression', 'function_call_expression', 'member_call_expression', 'scoped_call_expression',
        'macro_invocation', 'method_call_expression', 'function_call', 'object_creation_expression', 'new_expression'}
ASSIGN = {'assignment_expression', 'assignment', 'augmented_assignment', 'assignment_statement', 'augmented_assignment_expression', 'compound_assignment_expr', 'short_var_declaration'}
BOOLOP = {'binary_expression', 'boolean_operator', 'logical_expression', 'binary_operator', 'infix_expression'}
BOOLTOK = {'&&', '||', 'and', 'or', '??', '?:'}
CONTROL = LOOP, IFS, SWITCH, TRY
CLOSURE = re.compile(r'(lambda|closure|anonymous_function|arrow_function|function_expression|block_argument|^block$|do_block)')
MUTSIDE = re.compile(r'(member|attribute|subscript|field|selector|index|element|navigation|property)')
SELF = {'this', 'self', '$this'}

def role_of(path):
    """Path -> role bucket shared across repositories and languages (hand-set keyword heuristic)."""
    p = path.lower()
    for role, rx in (('server', r'(^|/)(api|server|servers|controller|controllers|handler|handlers|route|routes|routing|http|web|rest|endpoint|endpoints|rpc|grpc|cmd|cli)(/|$)'),
                     ('data', r'(^|/)(model|models|entity|entities|db|database|store|storage|repository|repositories|dao|orm|schema|migrations?)(/|$)'),
                     ('ui', r'(^|/)(ui|view|views|component|components|page|pages|widget|widgets|frontend|client|gui|render|rendering|layout|style|styles)(/|$)'),
                     ('util', r'(^|/)(util|utils|utility|helper|helpers|common|shared|base|support|misc|tools?)(/|$)'),
                     ('core', r'(^|/)(core|service|services|domain|engine|compiler|compile|runtime|vm|kernel|lib|libs|internal|pkg|src)(/|$)')):
        if re.search(rx, p): return role
    return 'other'

def c_declarator_name(node):
    d = node.child_by_field_name('declarator')
    while d is not None:
        nxt = d.child_by_field_name('declarator')
        if nxt is None: break
        d = nxt
    if d is None: return None
    if d.type in ('qualified_identifier', 'scoped_identifier'): d = d.child_by_field_name('name') or d
    return d

def fname(node, lang, src):
    n = node.child_by_field_name('name')
    if n is None and lang in ('c', 'cpp'): n = c_declarator_name(node)
    if n is None and lang == 'perl':
        for c in node.children:
            if c.type == 'bareword': n = c; break
    if n is None and node.type in ('arrow_function', 'function_expression') and node.parent is not None:
        p = node.parent
        if p.type in ('variable_declarator', 'pair', 'public_field_definition', 'assignment_expression'):
            n = p.child_by_field_name('name') or p.child_by_field_name('key') or p.child_by_field_name('left')
    if n is None: return None
    return n.text.decode('utf8', 'replace')[:80]

def callee_text(node):
    f = node.child_by_field_name('function') or node.child_by_field_name('name') or node.child_by_field_name('method')
    obj = node.child_by_field_name('object') or node.child_by_field_name('receiver')
    if f is None and node.children: f = node.children[0]
    t = f.text.decode('utf8', 'replace') if f is not None else ''
    if obj is not None and f is not None and node.type in ('method_invocation', 'member_call_expression', 'method_call_expression'):
        t = obj.text.decode('utf8', 'replace') + '.' + t
    return re.sub(r'\s+', '', t)[:120]

def analyze(node, lang, in_class):
    c = dict(loops=0, chain=0, mutate=0, lets=0, consts=0, awaits=0, thens=0, throws=0, tries=0, sw=0, tern=0, ifs=0, opt=0, thisUse=0, maxDepth=0, cyc=1, calls=0, nonNull=0, closures=0)
    callees = []
    stack = [(node, 0)]
    while stack:
        n, depth = stack.pop(); t = n.type
        ctl = False
        if LOOP.search(t): c['loops'] += 1; c['cyc'] += 1; ctl = True
        elif t in IFS: c['ifs'] += 1; c['cyc'] += 1; ctl = True
        elif t in SWITCH: c['sw'] += 1; ctl = True
        elif t in TRY: c['tries'] += 1; ctl = True
        elif t in CATCH: c['cyc'] += 1
        elif t in TERN: c['tern'] += 1; c['cyc'] += 1
        elif t in THROW: c['throws'] += 1
        elif t in AWAIT: c['awaits'] += 1
        if t in BOOLOP:
            op = n.child_by_field_name('operator')
            if op is not None and op.type in BOOLTOK: c['cyc'] += 1
        if t in ASSIGN:
            left = n.child_by_field_name('left') or (n.children[0] if n.children else None)
            if left is not None and MUTSIDE.search(left.type): c['mutate'] += 1
        if CLOSURE.search(t) and n is not node: c['closures'] += 1; ctl = True
        if t in ('identifier', 'this', 'self', 'variable_name') and n.text in (b'this', b'self', b'$this'): c['thisUse'] += 1
        if t in ('optional_chain', 'safe_navigation', 'conditional_access_expression'): c['opt'] += 1
        if t == 'non_null_expression': c['nonNull'] += 1
        if t in ('lexical_declaration', 'variable_declaration', 'let_declaration', 'property_declaration', 'val_definition', 'var_definition', 'local_variable_declaration'):
            tx = n.text[:12]
            if lang in ('rust',): mutable = tx.startswith(b'let mut')
            elif lang in ('swift', 'kotlin', 'scala'): mutable = tx.lstrip().startswith((b'var', b'private var', b'public var')) or b'var ' in tx[:8]
            else: mutable = tx.startswith((b'let ', b'var '))
            c['lets' if mutable else 'consts'] += 1
        if lang == 'elixir' and t == 'call' and n.children:
            kw = n.children[0].text
            if kw in (b'if', b'unless'): c['ifs'] += 1; c['cyc'] += 1; ctl = True
            elif kw in (b'case', b'cond', b'with'): c['sw'] += 1; ctl = True
            elif kw == b'for': c['loops'] += 1; c['cyc'] += 1; ctl = True
            elif kw in (b'try', b'rescue'): c['tries'] += 1; ctl = True
            elif kw in (b'raise', b'throw'): c['throws'] += 1
        if t in CALL:
            c['calls'] += 1
            ct = callee_text(n)
            if ct:
                if len(callees) < 60: callees.append(ct)
                m = re.split(r'[.:>\-]+', ct)[-1]
                if ')' in ct: c['chain'] += 1
                if m == 'then' or m == 'catch': c['thens'] += 1
                if m in ('unwrap', 'expect', 'force_unwrap'): c['nonNull'] += 1
        d2 = depth + 1 if ctl else depth
        if d2 > c['maxDepth']: c['maxDepth'] = d2
        for ch in n.children: stack.append((ch, d2))
    return c, callees

def units_of(tree, lang, src, rel):
    out = []
    funcs = FUNC[lang]
    stack = [(tree.root_node, False)]
    while stack:
        n, in_class = stack.pop()
        t = n.type
        cls = in_class or bool(CLASS.match(t)) or (t == 'method_declaration' and lang == 'go')
        is_fn = t in funcs
        if lang == 'elixir' and t == 'call' and n.children and n.children[0].text in (b'def', b'defp', b'defmacro', b'defmacrop'):
            is_fn = True
        if is_fn:
            start, end = n.start_point[0], n.end_point[0]
            if end - start + 1 >= 3:
                if lang == 'elixir':
                    args = n.children[1] if len(n.children) > 1 else None
                    nm = None
                    if args is not None and args.children:
                        a0 = args.children[0]; nm = (a0.children[0].text if a0.type == 'call' and a0.children else a0.text).decode('utf8', 'replace')[:80]
                else:
                    nm = fname(n, lang, src)
                if nm:
                    c, callees = analyze(n, lang, cls)
                    c.update(file=rel, name=nm, cls='class' if cls else None, line=start + 1, loc=end - start + 1, callees=callees, lang=lang, async_=c['awaits'] > 0)
                    out.append(c)
            # nested functions are counted inside this unit; do not descend for new units
            continue
        for ch in n.children: stack.append((ch, cls))
    return out

def main():
    root, repo, outdir = sys.argv[1:4]
    mx = int(sys.argv[sys.argv.index('--max-units') + 1]) if '--max-units' in sys.argv else 20000
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 0
    os.makedirs(outdir, exist_ok=True)
    parsers = {}; units = []; nfiles = 0; nerr = 0
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d != '.git']
        for f in sorted(fs):
            ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
            lang = EXT.get(ext)
            if not lang: continue
            p = os.path.join(r, f); rel = os.path.relpath(p, root)
            if SKIP.search(rel.lower()): continue
            try:
                if os.path.getsize(p) > 1_500_000: continue
                src = open(p, 'rb').read()
                if lang not in parsers: parsers[lang] = get_parser('tsx' if lang == 'tsx' else lang)
                tree = parsers[lang].parse(src)
            except Exception:
                nerr += 1; continue
            nfiles += 1
            role = role_of(rel)
            for u in units_of(tree, lang, src, rel):
                u['layer'] = f'{lang}:{role}'; u['repo'] = repo; units.append(u)
    total = len(units)
    random.Random(seed).shuffle(units)
    units = units[:mx]
    path = os.path.join(outdir, repo.replace('/', '_') + '.units.jsonl.gz')
    with gzip.open(path, 'wt') as f:
        for u in units: f.write(json.dumps(u) + '\n')
    langs = {}
    for u in units: langs[u['lang']] = langs.get(u['lang'], 0) + 1
    print(f'{repo}: {nfiles} files, {nerr} unreadable, {total} units, kept {len(units)} {langs}')

if __name__ == '__main__':
    main()
