"""Preset v2: instance-aware propagation (Python-specific AST analysis).

On top of build_preset.py (seed tags + cross-module call graph) this adds object semantics:
  - local typing:      x = Cls(...)  /  with Cls(...) as x  /  x = factory(...)  ->  x.method() is Cls.method (through base classes)
  - return types:      a function that returns Cls(...) (or a variable typed Cls) is a factory for Cls
  - instance attrs:    self.a = Cls(...) / self.a = some_function in any method  ->  self.a.method() / self.a(...) resolve
  - parameter binding: a class/function passed as an argument is what a call on the parameter may reach (context-insensitive)
  - escape:            an instance passed to another call may have its public methods called back (switchable, `ESCAPE`)
"""
import ast, collections, json, sys
sys.path.insert(0, '.')
from build_preset import Preset, Mod, dotted, iter_defs, iter_stmts, IO_TAGS, NATIVE, BUILTIN_SEEDS, SYS_SEEDS, METHOD_SEEDS, DIAGNOSTIC, FAM

ESCAPE = {'on': True}

class Preset2(Preset):
    def __init__(self, escape=True, rounds=3):
        ESCAPE['on'] = escape
        super().__init__()                      # v1 graph first (also gives the module table)
        self.rounds = rounds
        self.bases = {}                         # class key -> [base class keys]
        for m in self.mods.values():
            for n in iter_defs(m.tree.body):
                if isinstance(n, ast.ClassDef):
                    ck = f'{m.name}.{n.name}'; bs = []
                    for b in n.bases:
                        d = dotted(b)
                        if d:
                            r = self.ref(m, d)
                            if r and r[0] == 'class': bs.append(r[1])
                    self.bases[ck] = bs
        self.ret = collections.defaultdict(set)        # func key -> {class key}
        self.attr = collections.defaultdict(set)       # (class key, attr) -> {ref}
        self.param = collections.defaultdict(set)      # (func key, param) -> {ref}
        self.analyze_all()

    # ---- references: ('class', ck) | ('func', fk) | ('tag', t) | None -----------------------------------------
    def ref(self, m, dotted_name, env=None):
        parts = dotted_name.split('.')
        if env and parts[0] in env and len(parts) == 1:
            return None
        root = parts[0]
        if root in m.top:
            n = m.top[root]
            if isinstance(n, ast.ClassDef) and len(parts) == 1: return ('class', f'{m.name}.{root}')
            if isinstance(n, ast.ClassDef) and len(parts) == 2: return ('func', f'{m.name}.{root}.{parts[1]}')
            if len(parts) == 1: return ('func', f'{m.name}.{root}')
        if root in m.alias: full = '.'.join([m.alias[root]] + parts[1:])
        elif root in BUILTIN_SEEDS and len(parts) == 1: return ('tag', BUILTIN_SEEDS[root])
        else:
            for s in m.star:
                r = self.ref_full(f'{s}.{dotted_name}')
                if r: return r
            return None
        return self.ref_full(full)

    def ref_full(self, full, depth=0):
        if depth > 6: return None
        parts = full.split('.')
        if parts[0] in DIAGNOSTIC: return None
        for i in range(len(parts), 0, -1):
            mod = '.'.join(parts[:i]); rest = parts[i:]
            if mod in NATIVE or mod in ('builtins', 'sys'):
                if rest:
                    t = self.native_tag(mod, rest[0]); return ('tag', t) if t else None
                return None
            if mod in self.mods and rest:
                m = self.mods[mod]; head = rest[0]
                if head in m.top:
                    n = m.top[head]
                    if isinstance(n, ast.ClassDef):
                        if len(rest) == 1: return ('class', f'{m.name}.{head}')
                        if len(rest) == 2: return ('func', f'{m.name}.{head}.{rest[1]}') if f'{m.name}.{head}.{rest[1]}' in m.funcs else None
                    elif len(rest) == 1: return ('func', f'{m.name}.{head}')
                    return None
                if head in m.alias: return self.ref_full('.'.join([m.alias[head]] + rest[1:]), depth + 1)
                for s in m.star:
                    r = self.ref_full('.'.join([s, head] + rest[1:]), depth + 1)
                    if r: return r
                return None
        return None

    def method(self, ck, name, seen=None):
        """find ck.name through base classes -> func key | None"""
        seen = seen or set()
        if ck in seen: return None
        seen.add(ck); k = f'{ck}.{name}'
        mod = ck.rsplit('.', 1)[0]
        for mm in (self.mods.get(mod),):
            if mm and k in mm.funcs: return k
        for b in self.bases.get(ck, []):
            r = self.method(b, name, seen)
            if r: return r
        return None

    def ctor(self, ck):
        return self.method(ck, '__init__')

    # ---- per-function analysis ---------------------------------------------------------------------------------
    def expr_types(self, m, fk, env, e):
        """set of refs an expression may evaluate to (class objects, functions, instances as ('inst', ck))."""
        out = set()
        if isinstance(e, ast.Call):
            for t in self.targets(m, fk, env, e.func, record=False):
                if t[0] == 'class': out.add(('inst', t[1]))
                elif t[0] == 'func':
                    for ck in self.ret.get(t[1], ()): out.add(('inst', ck))
        elif isinstance(e, (ast.Name, ast.Attribute)):
            d = dotted(e)
            if d:
                root = d.split('.')[0]
                if root in env and len(d.split('.')) == 1: out |= env[root]
                elif root in ('self', 'cls') and len(d.split('.')) == 2:
                    ck = fk.rpartition('.')[0]
                    for c in [ck] + self.all_bases(ck): out |= self.attr.get((c, d.split('.')[1]), set())
                else:
                    r = self.ref(m, d)
                    if r: out.add(r)
        elif isinstance(e, ast.IfExp):
            out |= self.expr_types(m, fk, env, e.body) | self.expr_types(m, fk, env, e.orelse)
        elif isinstance(e, ast.BoolOp):
            for v in e.values: out |= self.expr_types(m, fk, env, v)
        return out

    def all_bases(self, ck, seen=None):
        seen = seen if seen is not None else set(); out = []
        for b in self.bases.get(ck, []):
            if b not in seen: seen.add(b); out.append(b); out += self.all_bases(b, seen)
        return out

    def targets(self, m, fk, env, f, record=True):
        """what a call to `f` may reach: set of ('tag',t) | ('func',key) | ('class',ck) (class => constructor)"""
        out = set()
        if isinstance(f, ast.Name):
            if f.id in env:                                      # local variable / parameter holding a function or class
                for t in env[f.id]:
                    if t[0] in ('func', 'class', 'tag'): out.add(t)
                if out: return out
                return out
            r = self.ref(m, f.id)
            if r: out.add(r)
            return out
        if isinstance(f, ast.Attribute):
            d = dotted(f)
            if d:
                root = d.split('.')[0]; chain = d.split('.')[1:]
                if root in ('self', 'cls') and chain:
                    ck = fk.rpartition('.')[0]
                    if len(chain) == 1:
                        mk = self.method(ck, chain[0])
                        if mk: out.add(('func', mk))
                        for c in [ck] + self.all_bases(ck):
                            for t in self.attr.get((c, chain[0]), ()):
                                if t[0] in ('func', 'tag'): out.add(t)
                        for ck2 in self.subclasses_with(ck, chain[0]): out.add(('func', ck2))   # method possibly overridden
                        return out
                    # self.attr.method(...)
                    for c in [ck] + self.all_bases(ck):
                        for t in self.attr.get((c, chain[0]), ()):
                            if t[0] == 'inst' and len(chain) == 2:
                                mk = self.method(t[1], chain[1])
                                if mk: out.add(('func', mk))
                    if out: return out
                elif root in env and chain:
                    for t in env[root]:
                        if t[0] == 'inst' and len(chain) == 1:
                            mk = self.method(t[1], chain[0])
                            if mk: out.add(('func', mk))
                        elif t[0] == 'mod' : pass
                    if out: return out
                r = self.ref(m, d)
                if r: return {r}
            if isinstance(f.value, ast.Call):                    # Cls(...).method() / factory().method()
                for t in self.expr_types(m, fk, env, f.value):
                    if t[0] == 'inst':
                        mk = self.method(t[1], f.attr)
                        if mk: out.add(('func', mk))
                if out: return out
            if f.attr in METHOD_SEEDS: out.add(('tag', METHOD_SEEDS[f.attr]))
        return out

    def subclasses_with(self, ck, name):
        if not hasattr(self, '_sub'):
            self._sub = collections.defaultdict(list)
            for c, bs in self.bases.items():
                for b in bs: self._sub[b].append(c)
        res = []
        for s in self._sub.get(ck, []):
            mm = self.mods.get(s.rsplit('.', 1)[0]); k = f'{s}.{name}'
            if mm and k in mm.funcs: res.append(k)
        return res

    def analyze_function(self, m, fk, fn):
        args = fn.args; params = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs] + ([args.vararg.arg] if args.vararg else [])
        env = {p: set(self.param.get((fk, p), ())) for p in params if p not in ('self', 'cls')}
        direct, edges = set(), set()
        stmts = list(ast.walk(fn))
        # typing pass (statement order approximated by ast.walk order, adequate for straight-line factories)
        for n in stmts:
            if isinstance(n, ast.Assign):
                ts = self.expr_types(m, fk, env, n.value)
                for tg in n.targets:
                    if isinstance(tg, ast.Name) and ts: env.setdefault(tg.id, set()).update(ts)
                    elif isinstance(tg, ast.Attribute) and isinstance(tg.value, ast.Name) and tg.value.id in ('self', 'cls') and ts:
                        self.attr[(fk.rpartition('.')[0], tg.attr)] |= ts
            elif isinstance(n, ast.withitem) and n.optional_vars is not None and isinstance(n.optional_vars, ast.Name):
                ts = self.expr_types(m, fk, env, n.context_expr)
                if ts: env.setdefault(n.optional_vars.id, set()).update(ts)
            elif isinstance(n, ast.Return) and n.value is not None:
                for t in self.expr_types(m, fk, env, n.value):
                    if t[0] == 'inst': self.ret[fk].add(t[1])
        # call pass
        for c in stmts:
            if isinstance(c, (ast.Attribute, ast.Name)):
                dd = dotted(c)
                if dd:
                    root = dd.split('.')[0]; full = '.'.join([m.alias.get(root, root)] + dd.split('.')[1:])
                    if full in ('os.environ', 'posix.environ', 'nt.environ'): direct.add('env')
                    elif full in ('sys.stdout', 'sys.stderr', 'sys.stdin'): direct.add('console')
                    elif full == 'environ' and any(s_ in ('posix', 'nt') for s_ in m.star): direct.add('env')
            if isinstance(c, ast.Call):
                for t in self.targets(m, fk, env, c.func):
                    if t[0] == 'tag': direct.add(t[1])
                    elif t[0] == 'func': edges.add(t[1])
                    elif t[0] == 'class':
                        ct = self.ctor(t[1])
                        if ct: edges.add(ct)
                        if ESCAPE['on']: pass
                    # bind class/function arguments to the callee's parameters
                    if t[0] in ('func', 'class'):
                        callee = t[1] if t[0] == 'func' else self.ctor(t[1])
                        cm = self.mods.get(callee.rsplit('.', 1)[0]) if callee else None
                        if callee and callee.count('.') >= 1:
                            cfn = self._fn(callee)
                            if cfn is not None:
                                cp = [a.arg for a in cfn.args.posonlyargs + cfn.args.args]
                                off = 1 if cp and cp[0] in ('self', 'cls') else 0
                                for i, a in enumerate(c.args):
                                    if i + off < len(cp):
                                        for r in self.expr_types(m, fk, env, a):
                                            if r[0] in ('class', 'func', 'tag'): self.param[(callee, cp[i + off])].add(r)
                                for kw in c.keywords:
                                    if kw.arg:
                                        for r in self.expr_types(m, fk, env, kw.value):
                                            if r[0] in ('class', 'func', 'tag'): self.param[(callee, kw.arg)].add(r)
                # escape: instances passed as arguments may be called back through their public methods
                if ESCAPE['on']:
                    for a in list(c.args) + [k.value for k in c.keywords]:
                        for r in self.expr_types(m, fk, env, a):
                            if r[0] == 'inst':
                                for k2 in self._public_methods(r[1]): edges.add(k2)
        return direct, edges

    def _fn(self, key):
        mod = key.rsplit('.', 1)[0]
        while mod and mod not in self.mods: mod = mod.rsplit('.', 1)[0] if '.' in mod else ''
        m = self.mods.get(mod); return m.funcs.get(key) if m else None

    def _public_methods(self, ck):
        mm = self.mods.get(ck.rsplit('.', 1)[0])
        if not mm: return []
        pre = ck + '.'
        return [k for k in mm.funcs if k.startswith(pre) and k.count('.') == ck.count('.') + 1 and not k.rpartition('.')[2].startswith('_')]

    def analyze_all(self, only=None):
        for _ in range(self.rounds):
            for m in self.mods.values():
                for key, fn in m.funcs.items():
                    if only and m.name not in only: continue
                    d, e = self.analyze_function(m, key, fn)
                    self.direct[key] = d; self.edges[key] = e
        self.tags = {k: set(v) for k, v in self.direct.items()}
        changed = True
        while changed:
            changed = False
            for k, es in self.edges.items():
                for e in es:
                    t = self.tags.get(e)
                    if t and not t <= self.tags[k]: self.tags[k] |= t; changed = True

    def add_module(self, name, src):
        """analyze user code as one more module (same machinery), then re-close tags"""
        m = Mod.__new__(Mod)
        tmp = ast.parse(src)
        import types, build_preset
        # reuse Mod parsing by writing through a temp file
        import tempfile, os
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f: f.write(src); p = f.name
        m = Mod(name, p); os.unlink(p)
        self.mods[name] = m
        for ck in [f'{name}.{n.name}' for n in iter_defs(m.tree.body) if isinstance(n, ast.ClassDef)]: self.bases[ck] = []
        for n in iter_defs(m.tree.body):
            if isinstance(n, ast.ClassDef):
                bs = []
                for b in n.bases:
                    d = dotted(b)
                    if d:
                        r = self.ref(m, d)
                        if r and r[0] == 'class': bs.append(r[1])
                self.bases[f'{name}.{n.name}'] = bs
        for _ in range(self.rounds):
            for key, fn in m.funcs.items():
                d, e = self.analyze_function(m, key, fn); self.direct[key] = d; self.edges[key] = e
        for key in m.funcs:
            self.tags[key] = set(self.direct[key])
        changed = True
        while changed:
            changed = False
            for key in m.funcs:
                for e in self.edges[key]:
                    t = self.tags.get(e)
                    if t and not t <= self.tags[key]: self.tags[key] |= t; changed = True
        return m

if __name__ == '__main__':
    for esc in (False, True):
        P = Preset2(escape=esc)
        funcs = {k: sorted(v) for k, v in P.tags.items() if v and not k.rpartition('.')[2].startswith('_')}
        by = collections.Counter(t for v in funcs.values() for t in v)
        print('escape', esc, 'tagged public', len(funcs), dict(by))
        if esc: json.dump(dict(language='python', version='v2 instance-aware', functions=funcs), open('preset_python2.json', 'w'), indent=0)
