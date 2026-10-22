"""Recursive AST tokenizer that is name-free (structure only) and resolves every call, through local helpers,
down to OS/platform API leaves (os.listdir, urllib.request.urlopen, builtin open, ...).

tokens(code) -> structure tokens, with Call nodes written as CALL:api:<qualified api name> / CALL:local / CALL:builtin:<name> / CALL:opaque.
leaves(code) -> {function name: set of platform-API leaves reachable through local calls}
category(code) -> (top, sub) by rules over the reachable leaves (see terms.md section 20).
"""
import ast, builtins, textwrap

# (module prefix) -> (top, sub). Longest prefix wins.
PLATFORM = {
    'os.system': ('io', 'process'), 'os.popen': ('io', 'process'), 'os.environ': ('io', 'environment'), 'os.getenv': ('io', 'environment'),
    'os': ('io', 'filesystem'), 'os.path': ('io', 'filesystem'), 'pathlib': ('io', 'filesystem'), 'shutil': ('io', 'filesystem'),
    'glob': ('io', 'filesystem'), 'fnmatch': ('io', 'filesystem'), 'tempfile': ('io', 'filesystem'), 'io': ('io', 'filesystem'),
    'filecmp': ('io', 'filesystem'), 'stat': ('io', 'filesystem'), 'zipfile': ('io', 'filesystem'), 'tarfile': ('io', 'filesystem'),
    'socket': ('io', 'network'), '_socket': ('io', 'network'), 'ssl': ('io', 'network'), 'http': ('io', 'network'), 'urllib': ('io', 'network'),
    'ftplib': ('io', 'network'), 'smtplib': ('io', 'network'), 'requests': ('io', 'network'), 'select': ('io', 'network'),
    'subprocess': ('io', 'process'), 'sys.stdout': ('io', 'console'), 'sys.stdin': ('io', 'console'), 'sys.stderr': ('io', 'console'),
    'time': ('io', 'clock'), 'random': ('io', 'environment'),
}
BUILTIN_API = {'open': ('io', 'filesystem'), 'print': ('io', 'console'), 'input': ('io', 'console')}
# object methods whose receiver type is unknown; resolved by what else the function reaches
FS_METHODS = {'read_text', 'write_text', 'read_bytes', 'write_bytes', 'iterdir', 'mkdir', 'unlink', 'rmdir', 'exists', 'is_file', 'is_dir', 'stat', 'tofile', 'fromfile'}
NET_METHODS = {'urlopen', 'connect', 'sendall', 'send', 'recv', 'recvfrom', 'getresponse', 'sendmail', 'login', 'getaddrinfo', 'bind', 'listen', 'accept'}
STREAM_METHODS = {'read', 'write', 'readline', 'readlines', 'flush', 'close'}
PURE_BUILTINS = set(dir(builtins)) - set(BUILTIN_API)

def _lookup(dotted):
    parts = dotted.split('.')
    for n in range(len(parts), 0, -1):
        p = '.'.join(parts[:n])
        if p in PLATFORM: return PLATFORM[p]
    return None

def _aliases(tree):
    al = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names: al[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names: al[a.asname or a.name] = n.module + '.' + a.name
    return al

def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute): parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name): parts.append(node.id); return '.'.join(reversed(parts))
    return None

class Unit:
    """One module (or one snippet): local defs, aliases, per-function direct call classification."""
    def __init__(self, src):
        self.tree = ast.parse(src); self.alias = _aliases(self.tree)
        self.defs = {}   # name -> FunctionDef (methods by bare name too)
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): self.defs.setdefault(n.name, n)
            if isinstance(n, ast.ClassDef): self.defs.setdefault(n.name, n)   # constructing a class calls __init__
        self.direct = {}; self.callees = {}
        for name, d in self.defs.items(): self.direct[name], self.callees[name] = self._scan(d)
        self.reach = self._closure()

    def classify_call(self, c):
        """-> ('api', qualified, (top,sub)) | ('local', name) | ('builtin', name) | ('method', attr) | ('opaque', name)"""
        f = c.func
        if isinstance(f, ast.Name):
            if f.id in self.defs: return ('local', f.id)
            if f.id in self.alias:
                q = self.alias[f.id]; r = _lookup(q)
                return ('api', q, r) if r else ('lib', q)
            if f.id in BUILTIN_API: return ('api', f.id, BUILTIN_API[f.id])
            if f.id in PURE_BUILTINS: return ('builtin', f.id)
            return ('opaque', f.id)
        if isinstance(f, ast.Attribute):
            d = _dotted(f)
            if d:
                root = d.split('.')[0]
                if root in self.alias:
                    q = self.alias[root] + d[len(root):]; r = _lookup(q)
                    return ('api', q, r) if r else ('lib', q)
                if root == 'self' and f.attr in self.defs: return ('local', f.attr)
                if root == 'self' and f.attr not in STREAM_METHODS and f.attr not in NET_METHODS and f.attr not in FS_METHODS: return ('opaque', d)
            if f.attr in self.defs and f.attr not in STREAM_METHODS: return ('local', f.attr)
            if f.attr in NET_METHODS: return ('api', '.' + f.attr, ('io', 'network'))
            if f.attr in FS_METHODS: return ('api', '.' + f.attr, ('io', 'filesystem'))
            if f.attr in STREAM_METHODS: return ('method', f.attr)
            return ('method', f.attr)
        return ('opaque', '?')

    def _scan(self, fn):
        api, local = set(), set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                k = self.classify_call(n)
                if k[0] == 'api': api.add((k[1], k[2]))
                elif k[0] == 'local': local.add(k[1])
        return api, local

    def _closure(self):
        reach = {k: set(v) for k, v in self.direct.items()}
        changed = True
        while changed:
            changed = False
            for k in reach:
                for c in self.callees[k]:
                    if c in reach and not reach[c] <= reach[k]: reach[k] |= reach[c]; changed = True
        return reach

def struct_tokens(unit, fn):
    """Pre-order node-type tokens, name-free. Calls carry their resolution; local calls are followed by the callee's API leaves."""
    out = []
    def visit(n, depth=0):
        t = type(n).__name__
        if isinstance(n, ast.Call):
            k = unit.classify_call(n)
            if k[0] == 'api': out.append('CALL:api:' + k[1])
            elif k[0] == 'local':
                out.append('CALL:local')
                for q, _ in sorted(unit.reach.get(k[1], ())): out.append('LEAF:' + q)
            elif k[0] == 'builtin': out.append('CALL:builtin:' + k[1])
            elif k[0] == 'lib': out.append('CALL:lib:' + k[1].split('.')[0])
            elif k[0] == 'method': out.append('CALL:method')
            else: out.append('CALL:opaque')
        elif isinstance(n, ast.Constant): out.append('Const:' + type(n.value).__name__)
        elif isinstance(n, ast.BinOp): out.append('BinOp:' + type(n.op).__name__)
        elif isinstance(n, ast.Compare): out.append('Compare:' + ','.join(type(o).__name__ for o in n.ops))
        elif isinstance(n, ast.arg) or isinstance(n, ast.Name) or isinstance(n, ast.Attribute):
            out.append(t + ('@self' if (isinstance(n, ast.Name) and n.id == 'self') else ''))
        else: out.append(t)
        for c in ast.iter_child_nodes(n):
            if isinstance(n, ast.Call) and c is n.func: continue
            visit(c, depth + 1)
        if isinstance(n, ast.Call):
            for c in ast.iter_child_nodes(n.func): visit(c, depth + 1)
    visit(fn); return out

def category(unit, names):
    """Category of the unit's entry functions `names`: platform leaves reached -> io/<sub>; else glue vs compute by shape."""
    leaves = set()
    for nm in names: leaves |= unit.reach.get(nm, set())
    # stream methods resolved by neighbours
    if leaves:
        subs = [s for _, (t, s) in leaves]
        net = subs.count('network'); fs = subs.count('filesystem')
        sub = 'network' if net > 0 and net >= fs else max(set(subs), key=lambda s: (subs.count(s), s))
        return ('io', sub), leaves
    # no platform leaf: stream-method-only functions are IO too only if they call .read/.write on a non-local receiver
    calls = {'opaque': 0, 'local': 0, 'builtin': 0, 'method': 0, 'lib': 0}; compute = 0
    for nm in names:
        d = unit.defs[nm]
        for n in ast.walk(d):
            if isinstance(n, ast.Call): calls[unit.classify_call(n)[0] if unit.classify_call(n)[0] in calls else 'opaque'] += 1
            if isinstance(n, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.BinOp, ast.AugAssign, ast.Lambda)): compute += 1
            if isinstance(n, ast.Compare) and not all(isinstance(c, ast.Constant) and isinstance(c.value, str) for c in n.comparators): compute += 1
    delegated = calls['opaque'] + calls['local']
    if delegated >= 1 and compute == 0: return ('glue', 'compose'), leaves
    return ('compute', None), leaves
