"""Build a category PRESET for Python from a small hand-made OS-API tag set.

Seeds (hand-made, small): OS/native-module functions -> tag in {fs, net, proc, console, clock, env, random, thread}.
Everything else is derived: every stdlib function gets the union of tags of the seeds it reaches through the call graph
(cross-module, through re-exports such as `from posix import *`), so `shutil.copyfile`, `urllib.request.urlopen`,
`subprocess.run`, ... are tagged without being listed by hand.
Output: preset_python.json, and a loadable `Preset` for classification.
"""
import ast, importlib.util, json, os, sys, collections, sysconfig

IO_TAGS = {'fs', 'net', 'proc'}      # console/clock/env/random/thread are tags too, but do not make code 'IO' (prints and caches are everywhere)
# ---- the hand-made part: OS API families (POSIX man-2 groupings) -------------------------------------------------
POSIX_FAMILIES = {
 'fs': 'open close read write pread pwrite stat lstat fstat listdir scandir mkdir rmdir unlink remove rename replace chmod chown lchown link symlink '
       'readlink getcwd chdir truncate ftruncate fsync fdatasync utime access mkfifo mknod lseek dup dup2 pipe sendfile statvfs fstatvfs chroot umask '
       'realpath isatty ttyname fchmod fchown fdopen lstat sync copy_file_range',
 'proc': 'system fork forkpty execv execve execvp execl spawnv spawnl kill killpg wait waitpid wait3 wait4 abort _exit getpid getppid setsid nice '
         'posix_spawn register_at_fork',
 'env': 'getenv putenv unsetenv environ getlogin uname getuid getgid geteuid cpu_count sysconf confstr getloadavg',
 'random': 'urandom getrandom',
}
NATIVE = {   # native (C) module -> tag (all functions) or None => look up POSIX_FAMILIES by function name
 'posix': None, 'nt': None,
 '_socket': 'net', 'select': 'net', 'selectors': None, '_ssl': 'net', '_posixsubprocess': 'proc',
 'time': 'clock', '_io': 'fs', '_thread': 'thread', '_random': 'random', 'termios': 'console', 'pwd': 'env', 'grp': 'env', 'fcntl': 'fs', 'mmap': 'fs',
}
BUILTIN_SEEDS = {'open': 'fs', 'print': 'console', 'input': 'console'}
SYS_SEEDS = {'stdout': 'console', 'stderr': 'console', 'stdin': 'console', 'argv': 'env', 'exit': 'proc'}
# modules that only report problems (warnings, tracebacks, logging...): calls into them do not make a function "IO"
DIAGNOSTIC = {'warnings', 'traceback', 'logging', 'linecache', 'pdb', 'bdb', 'cProfile', 'profile', 'trace', 'faulthandler', 'code', 'codeop', 'pydoc', 'doctest', 'unittest', 'reprlib'}
# methods of native socket objects (receiver type unknown in Python source)
METHOD_SEEDS = {n: 'net' for n in 'send sendall recv recv_into recvfrom recvfrom_into sendto connect connect_ex bind listen accept getsockname getpeername setsockopt getsockopt settimeout'.split()}
FAM = {fn: tag for tag, names in POSIX_FAMILIES.items() for fn in names.split()}

SKIP = ('test', 'idlelib', 'turtledemo', 'lib2to3', 'pydoc_data', 'ensurepip', '__phello__', 'antigravity', 'this', '_pydecimal', 'tkinter', 'distutils')

def module_file(name):
    try: spec = importlib.util.find_spec(name)
    except Exception: return None
    if spec and spec.origin and spec.origin.endswith('.py'): return spec.origin
    if spec and spec.origin == 'frozen':          # frozen stdlib modules (os, io, abc, stat, posixpath, ...): read the file from the stdlib dir
        base = os.path.join(sysconfig.get_paths()['stdlib'], *name.split('.'))
        for cand in (base + '.py', os.path.join(base, '__init__.py')):
            if os.path.exists(cand): return cand
    return None

def dotted(x):
    parts = []
    while isinstance(x, ast.Attribute): parts.append(x.attr); x = x.value
    if isinstance(x, ast.Name): parts.append(x.id); return '.'.join(reversed(parts))
    return None

def iter_stmts(body):
    for n in body:
        yield n
        if isinstance(n, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            for sub in (getattr(n, 'body', []), getattr(n, 'orelse', []), getattr(n, 'finalbody', []), *[h.body for h in getattr(n, 'handlers', [])]):
                yield from iter_stmts(sub)

def iter_defs(body):
    for n in iter_stmts(body):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): yield n

class Mod:
    def __init__(self, name, path):
        self.name = name; self.tree = ast.parse(open(path, encoding='utf8', errors='ignore').read())
        self.alias = {}; self.star = []; self.top = {}; self.methods = collections.defaultdict(list); self.funcs = {}
        pkg = name if path.endswith('__init__.py') else name.rpartition('.')[0]
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Import):
                for a in n.names: self.alias[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
            elif isinstance(n, ast.ImportFrom):
                base = n.module or ''
                if n.level:
                    parts = pkg.split('.'); parts = parts[:len(parts) - (n.level - 1)]; base = '.'.join(parts + ([n.module] if n.module else []))
                for a in n.names:
                    if a.name == '*': self.star.append(base)
                    else: self.alias[a.asname or a.name] = base + '.' + a.name
        for n in iter_defs(self.tree.body):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): self.top[n.name] = n; self.funcs[f'{name}.{n.name}'] = n
            elif isinstance(n, ast.ClassDef):
                self.top[n.name] = n
                for m in iter_defs(n.body):
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.funcs[f'{name}.{n.name}.{m.name}'] = m; self.methods[m.name].append(f'{name}.{n.name}.{m.name}')
        # 3. simple module-level aliases:  X = mod.func  /  X = other_name
        for n in iter_stmts(self.tree.body):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                d = dotted(n.value)
                if d and n.targets[0].id not in self.top:
                    root = d.split('.')[0]
                    if root in self.alias: self.alias[n.targets[0].id] = '.'.join([self.alias[root]] + d.split('.')[1:])
                    elif d in BUILTIN_SEEDS: self.alias[n.targets[0].id] = 'builtins.' + d

class Preset:
    def __init__(self, mods=None):
        self.mods = {}
        names = sorted(n for n in sys.stdlib_module_names if not n.startswith(SKIP))
        extra = []
        for n in names:
            p = module_file(n)
            if p:
                self.mods[n] = Mod(n, p)
                if p.endswith('__init__.py'):
                    d = os.path.dirname(p)
                    for f in os.listdir(d):
                        if f.endswith('.py') and f != '__init__.py' and not f.startswith('test'): extra.append((f'{n}.{f[:-3]}', os.path.join(d, f)))
        for n, p in extra:
            try: self.mods[n] = Mod(n, p)
            except SyntaxError: pass
        for p, extra_name in (('posixpath', 'os.path'),):   # os.path is posixpath
            if p in self.mods: self.mods[extra_name] = self.mods[p]
        self.direct = {}; self.edges = {}
        for m in self.mods.values():
            for key, fn in m.funcs.items():
                if key in self.direct: continue
                d, e = set(), set()
                for c in ast.walk(fn):
                    if isinstance(c, (ast.Attribute, ast.Name)):
                        dd = dotted(c)
                        if dd:
                            root = dd.split('.')[0]; full = '.'.join([m.alias.get(root, root)] + dd.split('.')[1:])
                            if full in ('os.environ', 'posix.environ', 'nt.environ'): d.add('env')
                            elif full in ('sys.stdout', 'sys.stderr', 'sys.stdin'): d.add('console')
                            elif full == 'environ' and any(s_ in ('posix', 'nt') for s_ in m.star): d.add('env')
                    if isinstance(c, ast.Call):
                        r = self.resolve_call(m, c.func, owner=key)
                        if r is None: continue
                        (d if r[0] == 'tag' else e).add(r[1])
                self.direct[key] = d; self.edges[key] = e
        self.tags = {k: set(v) for k, v in self.direct.items()}
        changed = True
        while changed:
            changed = False
            for k, es in self.edges.items():
                for e in es:
                    t = self.tags.get(e)
                    if t and not t <= self.tags[k]: self.tags[k] |= t; changed = True
        self._mi = None

    # --- name resolution ---------------------------------------------------------------------------------------
    def native_tag(self, mod, name):
        t = NATIVE.get(mod)
        if mod in NATIVE:
            if t: return t
            return FAM.get(name)
        if mod == 'builtins': return BUILTIN_SEEDS.get(name)
        if mod == 'sys': return SYS_SEEDS.get(name)
        return None

    def resolve_full(self, full, depth=0):
        """'a.b.c' -> ('tag', t) | ('func', key) | None"""
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
                if head in m.top and len(rest) == 1:
                    if isinstance(m.top[head], ast.ClassDef):
                        k = f'{m.name}.{head}.__init__'; return ('func', k) if k in m.funcs else None
                    return ('func', f'{m.name}.{head}')
                if head in m.top and len(rest) == 2: return ('func', f'{m.name}.{head}.{rest[1]}') if f'{m.name}.{head}.{rest[1]}' in m.funcs else None
                if head in m.alias: return self.resolve_full('.'.join([m.alias[head]] + rest[1:]), depth + 1)
                for s in m.star:
                    r = self.resolve_full('.'.join([s, head] + rest[1:]), depth + 1)
                    if r: return r
                return None
        return None

    def resolve_call(self, m, f, owner=None):
        if isinstance(f, ast.Name):
            if f.id in m.top:
                if isinstance(m.top[f.id], ast.ClassDef):
                    k = f'{m.name}.{f.id}.__init__'; return ('func', k) if k in m.funcs else None
                return ('func', f'{m.name}.{f.id}')
            if f.id in m.alias: return self.resolve_full(m.alias[f.id])
            for s in m.star:
                r = self.resolve_full(f'{s}.{f.id}')
                if r: return r
            if f.id in BUILTIN_SEEDS: return ('tag', BUILTIN_SEEDS[f.id])
            return None
        if isinstance(f, ast.Attribute):
            parts = []; x = f
            while isinstance(x, ast.Attribute): parts.append(x.attr); x = x.value
            if isinstance(x, ast.Name):
                root = x.id; chain = list(reversed(parts))
                if root in ('self', 'cls') and len(chain) == 1 and owner:
                    cls = owner.rpartition('.')[0]; k = f'{cls}.{chain[0]}'
                    if k in m.funcs: return ('func', k)
                    return None
                if root in m.alias: return self.resolve_full('.'.join([m.alias[root]] + chain))
                if root in m.top and len(chain) == 1 and isinstance(m.top[root], ast.ClassDef): return ('func', f'{m.name}.{root}.{chain[0]}') if f'{m.name}.{root}.{chain[0]}' in m.funcs else None
                if root == 'sys' or root in NATIVE: return self.resolve_full('.'.join([root] + chain))
            if isinstance(f.value, ast.Call):                 # Cls(...).method(): type of the receiver is the class being constructed
                dd = dotted(f.value.func)
                if dd:
                    root = dd.split('.')[0]
                    full = '.'.join([m.alias.get(root, root)] + dd.split('.')[1:]) + '.' + f.attr
                    r = self.resolve_full(full)
                    if r: return r
            if f.attr in METHOD_SEEDS: return ('tag', METHOD_SEEDS[f.attr])
        return None

    def module_prior(self, modname, thr=0.4):
        """Dominant IO tag of a module if at least `thr` of its public functions reach that tag (covers dynamic dispatch, e.g. urlopen -> opener.open)."""
        if not hasattr(self, '_mp'):
            self._mp = {}
            for name, m in self.mods.items():
                keys = [k for k in m.funcs if not k.rpartition('.')[2].startswith('_')]
                if not keys: continue
                c = collections.Counter(t for k in keys for t in (self.tags.get(k, set()) & IO_TAGS))
                if c:
                    t, n = c.most_common(1)[0]
                    if n / len(keys) >= thr: self._mp[name] = t
        return self._mp.get(modname)

    def import_prior(self, modname, depth=0, seen=None):
        """IO tag a module inherits from the modules it imports that have a module prior (urllib.request -> http.client -> socket => net)."""
        seen = seen if seen is not None else set()
        if depth > 4 or modname in seen or modname not in self.mods: return None
        seen.add(modname); m = self.mods[modname]
        c = collections.Counter()
        for tgt in list(m.alias.values()) + m.star:
            parts = tgt.split('.')
            for i in range(len(parts), 0, -1):
                mod = '.'.join(parts[:i])
                if mod in NATIVE and NATIVE[mod] in IO_TAGS: c[NATIVE[mod]] += 1; break
                if mod in self.mods and mod != modname:
                    t = self.module_prior(mod) or self.import_prior(mod, depth + 1, seen)
                    if t: c[t] += 1
                    break
        return c.most_common(1)[0][0] if c else None

    # --- derived method-name index (receiver type unknown): use a method name only if stdlib definitions agree ------
    def method_tag(self, name):
        if self._mi is None:
            idx = collections.defaultdict(list)
            for m in self.mods.values():
                for k, fn in m.methods.items():
                    for key in fn: idx[k].append(self.tags.get(key, set()))
            self._mi = {}
            for k, ts in idx.items():
                tagged = [t for t in ts if t]
                if len(tagged) >= 1 and len(tagged) / len(ts) >= 0.8:
                    c = collections.Counter(tag for t in tagged for tag in t); top, cnt = c.most_common(1)[0]
                    if cnt / len(tagged) >= 0.8: self._mi[k] = top
        return self._mi.get(name)

if __name__ == '__main__':
    P = Preset()
    funcs = {k: sorted(v) for k, v in P.tags.items() if v and not k.rpartition('.')[2].startswith('_')}
    by = collections.Counter(t for v in funcs.values() for t in v)
    out = dict(language='python', version=sys.version.split()[0], seeds=dict(posix_families=POSIX_FAMILIES, native=NATIVE, builtins=BUILTIN_SEEDS, sys=SYS_SEEDS),
               stats=dict(modules=len(P.mods), functions_total=len(P.direct), tagged_public=len(funcs), per_tag=dict(by), seed_names=len(FAM) + len(NATIVE) + len(BUILTIN_SEEDS) + len(SYS_SEEDS)),
               functions=funcs)
    json.dump(out, open('preset_python.json', 'w'), indent=0)
    print(json.dumps(out['stats'], indent=1))
