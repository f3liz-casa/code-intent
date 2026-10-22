"""Name hashing and name-free AST style features/axes for Python snippets."""
import ast, builtins, hashlib, io, keyword, textwrap, tokenize

_STD_ATTRS = set()
for _t in (list, dict, set, str, tuple, int, float):
    _STD_ATTRS |= set(dir(_t))
_STD_ATTRS |= {'tolist', 'item', 'cumsum', 'argsort', 'astype', 'shape', 'dtype'}

def strip_docs(src):
    """Remove docstrings and comments."""
    t = ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body \
           and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return ast.unparse(t)

def hash_names(src):
    """Replace user-chosen identifiers (functions, classes, args, locals, attributes defined in the snippet)
    by stable hashes. Keeps keywords, builtins, imported names and stdlib/numpy method names."""
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names: imported.add((a.asname or a.name).split('.')[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names: imported.add(a.asname or a.name)
    keep = set(dir(builtins)) | imported | set(keyword.kwlist) | {'self'}
    def h(name):
        return 'v' + hashlib.md5(name.encode()).hexdigest()[:5]
    class R(ast.NodeTransformer):
        def visit_Name(self, n):
            if n.id not in keep: n.id = h(n.id)
            return n
        def visit_arg(self, n):
            if n.arg not in keep: n.arg = h(n.arg)
            return n
        def visit_FunctionDef(self, n):
            if n.name not in keep and n.name != '__init__' and not (n.name.startswith('__') and n.name.endswith('__')): n.name = h(n.name)
            self.generic_visit(n); return n
        def visit_ClassDef(self, n):
            n.name = h(n.name); self.generic_visit(n); return n
        def visit_Attribute(self, n):
            self.generic_visit(n)
            if n.attr not in _STD_ATTRS and not (isinstance(n.value, ast.Name) and n.value.id in imported):
                n.attr = h(n.attr)
            return n
    return ast.unparse(R().visit(tree))

MUT_METHODS = {'append', 'add', 'pop', 'setdefault', 'update', 'insert', 'remove', 'extend', 'clear', 'sort', 'reverse', 'popitem', 'discard'}
HOF = {'map', 'filter', 'reduce', 'sorted', 'accumulate', 'starmap', 'partial', 'chain', 'zip', 'enumerate'}
NUMPYISH = {'np', 'numpy', 'torch', 'jnp', 'pd'}

def features(src):
    t = ast.parse(textwrap.dedent(src))
    fdefs = [n for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    fnames = {f.name for f in fdefs}
    f = dict(nodes=0, mut=0, loops=0, expr=0, cls=0, selfuse=0, batch=0, rec=0, lam=0, comp=0, hof=0)
    assigned = {}
    for n in ast.walk(t):
        f['nodes'] += 1
        if isinstance(n, ast.AugAssign): f['mut'] += 1
        elif isinstance(n, ast.Assign) or isinstance(n, ast.AnnAssign):
            tg = n.targets if isinstance(n, ast.Assign) else [n.target]
            for x in tg:
                for y in ast.walk(x):
                    if isinstance(y, (ast.Attribute, ast.Subscript)) and isinstance(y.ctx, ast.Store): f['mut'] += 1
                    elif isinstance(y, ast.Name) and isinstance(y.ctx, ast.Store):
                        assigned[y.id] = assigned.get(y.id, 0) + 1
        elif isinstance(n, ast.Call):
            fn = n.func
            if isinstance(fn, ast.Attribute) and fn.attr in MUT_METHODS: f['mut'] += 1
            nm = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
            if nm in HOF: f['hof'] += 1
            if nm in fnames and any(nm == g.name and any(m is n for m in ast.walk(g)) for g in fdefs): f['rec'] += 1
        if isinstance(n, (ast.For, ast.While)): f['loops'] += 1
        if isinstance(n, ast.Lambda): f['lam'] += 1
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)): f['comp'] += 1
        if isinstance(n, (ast.Yield, ast.YieldFrom)): f['comp'] += 1
        if isinstance(n, ast.ClassDef): f['cls'] += 1
        if isinstance(n, ast.Name) and n.id == 'self': f['selfuse'] += 1
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in NUMPYISH: f['batch'] += 1
    f['mut'] += sum(v - 1 for v in assigned.values() if v > 1)  # rebinding
    f['expr'] = f['lam'] + f['comp'] + f['hof'] + f['rec']
    return f

AXES = ['mutation', 'object_binding', 'explicit_iteration', 'columnar_batch']
AXIS_DOC = {
 'mutation': 'how much the code changes existing state (aug-assign, attribute/subscript stores, mutating methods, rebinding), per 25 AST nodes, capped at 1',
 'object_binding': 'behaviour bundled with data: class definitions and self-use (0 = free functions)',
 'explicit_iteration': 'share of iteration done by statements (for/while) rather than expressions (comprehension, lambda, map/reduce, recursion); 0.5 if neither',
 'columnar_batch': 'whole-array/batch operations via numpy-like libraries, per 25 AST nodes, capped at 1',
}
def axes(src):
    f = features(src); n = max(f['nodes'], 1)
    mut = min(1.0, f['mut'] / n * 25 / 4)
    obj = min(1.0, 0.5 * (f['cls'] > 0) + min(0.5, f['selfuse'] / n * 25 / 4))
    it = f['loops'] + f['expr']
    expl = 0.5 if it == 0 else f['loops'] / it
    col = min(1.0, f['batch'] / n * 25 / 3)
    return [mut, obj, expl, col]
