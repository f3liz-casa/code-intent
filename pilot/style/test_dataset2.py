import os, tempfile, json, io, urllib.request, numpy as np
from unittest import mock
import dataset2
from dataset import S, STYLES
tmp = tempfile.mkdtemp(); p = os.path.join(tmp, 'a.txt'); open(p, 'w').write('  one \n\n two\n   \nthree')
for n in ['x.py', 'y.txt', 'z.py', 'q.md']: open(os.path.join(tmp, n), 'w').write('.')
open(os.path.join(tmp, 'b.json'), 'w').write(json.dumps([{"name": "a", "age": 20}, {"name": "b", "age": 3}]))
class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
state = {'n': 0}
def fake(url, timeout=None):
    state['n'] += 1
    if state['n'] % 3 != 0: raise OSError('boom')  # fail twice, then succeed
    return Resp(b'{"ok": [1, 2]}')
helpers = dict(
  read_json=lambda p: json.load(open(p)),
  adult_names=lambda ps: [p["name"] for p in ps if p["age"] >= 18],
  adult_names_columns=lambda n, a: [x for x, y in zip(n, a) if y >= 18],
  total_price=lambda items, tax: sum(p * q for p, q in items) * (1 + tax),
  total_price_columns=lambda p, q, tax: float(np.dot(p, q) * (1 + tax)))
CASES = {'read_lines': [(p,)], 'list_by_ext': [(tmp, '.py')], 'fetch_json': [('http://x',)],
         'glue_adults': [(os.path.join(tmp, 'b.json'),)], 'glue_report': [([(2.0, 3), (1.5, 2)], 0.1)],
         'glue_dispatch': [('sum', [1, 2, 3]), ('max', [1, 5, 2]), ('count', [4, 4])]}
bad = 0
def run(it, st, args):
    code, call = S[it][st]; ns = dict(helpers); exec(code, ns)
    if it == 'save_json':
        out = os.path.join(tmp, 'o_%s.json' % st); eval(call, {**ns, 'args': (out, {'a': [1, 2], 'b': 'x'})}); return json.load(open(out))
    if it == 'download':
        out = os.path.join(tmp, 'd_%s.bin' % st)
        with mock.patch('urllib.request.urlopen', lambda url, timeout=None: Resp(b'hello bytes')):
            n = eval(call, {**ns, 'args': ('http://x', out)})
        return (open(out, 'rb').read(), n)
    if it == 'fetch_json':
        state['n'] = 0
        with mock.patch('urllib.request.urlopen', fake): return eval(call, {**ns, 'args': args})
    return eval(call, {**ns, 'args': args})
cases = dict(CASES); cases['save_json'] = [None]; cases['download'] = [None]
for it, cs in cases.items():
    for args in cs:
        ref = None
        for st in STYLES:
            try: r = run(it, st, args)
            except Exception as e: r = ('ERR', repr(e))
            if ref is None: ref = r
            elif r != ref: bad += 1; print('MISMATCH', it, st, r, ref)
print('bad', bad, '| ref sample', ref)
