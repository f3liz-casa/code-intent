import ast, json, sys, textwrap
sys.path.insert(0, '.')
from dataset import S, STYLES
import dataset2
from dataset2 import CATEGORY
from stylelib import strip_docs, hash_names, axes

DESC = {
 'word_count': 'count how many times each word occurs in a text, ignoring case',
 'total_price': 'compute the total price of a list of (price, quantity) lines including tax',
 'adult_names': 'return the names of people who are at least 18 years old',
 'moving_average': 'compute the moving average of a list of numbers over a window of size k',
 'balanced': 'check whether the brackets in a string are balanced and properly nested',
 'flatten': 'flatten an arbitrarily nested list into a single flat list',
 'group_by': 'group records into lists by the value of a key field',
 'normalize': 'rescale a list of numbers to the range 0 to 1 using min-max scaling',
 'fib': 'return the first n Fibonacci numbers',
 'dedupe': 'remove duplicates from a list while keeping the first occurrence order',
 'top_k': 'return the k names with the highest scores',
 'balance': 'apply deposits and withdrawals to a starting balance, rejecting overdrafts',
 'read_lines': 'read a text file and return its non-blank lines with whitespace stripped',
 'list_by_ext': 'list the file names in a directory that end with a given extension, sorted',
 'save_json': 'write a Python object to a file as JSON',
 'fetch_json': 'fetch JSON from a URL over HTTP, retrying up to three times on network errors',
 'download': 'download the content of a URL into a local file and return the byte count',
 'glue_adults': 'load people from a JSON file and return the names of the adults, by combining existing helpers',
 'glue_report': 'build the line Total: X for a list of priced items by calling the existing price function',
 'glue_dispatch': 'route a command name (sum, max, count) to the matching handler and apply it to the values',
}
items = []
for it in S:
    for st in STYLES:
        raw = strip_docs(S[it][st][0])
        items.append(dict(kind='dataset', intent=it, style=st, top=CATEGORY[it][0], sub=CATEGORY[it][1], raw=raw, hashed=hash_names(raw)))

# real code: functions/methods of 5 existing modules, 8-60 lines, docstrings/comments stripped
import statistics, collections, argparse, numpy.lib._function_base_impl as npf, networkx.algorithms.shortest_paths.generic as nxg
import networkx.algorithms.shortest_paths.unweighted as nxu, networkx.algorithms.traversal.breadth_first_search as nxb
import shutil, glob, filecmp, urllib.request as urq, ftplib, smtplib
MODS = {'statistics': [statistics], 'collections': [collections], 'argparse': [argparse],
        'numpy_lib': [npf], 'networkx_paths': [nxg, nxu, nxb],
        'stdlib_fs': [shutil, glob, filecmp], 'stdlib_net': [urq, ftplib, smtplib]}
EXPECT = {'statistics': ('compute', 'numeric'), 'numpy_lib': ('compute', 'numeric'), 'networkx_paths': ('compute', 'logic'),
          'collections': ('compute', 'collections'), 'argparse': (None, None), 'stdlib_fs': ('io', 'filesystem'), 'stdlib_net': ('io', 'network')}
import inspect, random
random.seed(0)
real = []
for name, mods in MODS.items():
    got = []
    for m in mods:
        src = open(m.__file__).read()
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                seg = ast.get_source_segment(src, n)
                nl = seg.count('\n') + 1
                if not (8 <= nl <= 60): continue
                try: raw = strip_docs(textwrap.dedent(seg))
                except SyntaxError: continue
                if raw.count('\n') < 4: continue
                got.append(dict(kind='real', corpus=name, name=n.name, raw=raw, top=EXPECT[name][0], sub=EXPECT[name][1]))
    random.shuffle(got)
    real += got[:40 if name != 'networkx_paths' else 11]
for r in real: r['hashed'] = hash_names(r['raw'])
for r in items + real: r['axes'] = axes(r['raw'])
json.dump(dict(items=items + real, desc=DESC), open('texts.json', 'w'))
print(len(items), len(real), {c: sum(1 for r in real if r['corpus'] == c) for c in MODS})
