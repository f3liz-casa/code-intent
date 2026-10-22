"""Reverse lookup: Intent -> distribution of styles that already exist for it in the codebase.

usage: python3 -I intent_to_style.py <unit_styles.jsonl> --layer fe:util --cat pure --verb search [--min 15]

An Intent is (layer, effect category, name verb). Like the search code in sec. 27.1 it is matched in ordered steps,
each unit keeping the strongest step that matched (set-score-if-null); steps are run until at least --min units are found:
  3: layer + category + verb      2: layer + category      1: category + verb (any layer)      0: category (any layer)
The answer is a distribution over style clusters (what exists), where each cluster is shown with its profile and one example,
split into "this layer" and "elsewhere in the code base". It does not say which style is better.
"""
import argparse, collections, json, statistics

ap = argparse.ArgumentParser()
ap.add_argument('units'); ap.add_argument('--layer'); ap.add_argument('--cat', required=True); ap.add_argument('--verb')
ap.add_argument('--min', type=int, default=15)
a = ap.parse_args()

U = [json.loads(l) for l in open(a.units)]
for u in U:
    w = ''.join(c if c.islower() or not c.isalpha() else ' ' + c.lower() for c in (u['name'] or '')).split()
    u['verb'] = w[0] if w else ''

STEPS = [
    (3, 'layer+category+verb', lambda u: a.layer and a.verb and u['layer'] == a.layer and u['cat'] == a.cat and u['verb'] == a.verb),
    (2, 'layer+category', lambda u: a.layer and u['layer'] == a.layer and u['cat'] == a.cat),
    (1, 'category+verb', lambda u: a.verb and u['cat'] == a.cat and u['verb'] == a.verb),
    (0, 'category', lambda u: u['cat'] == a.cat),
]
score = {}
for i, (s, label, test) in enumerate(STEPS):
    if i > 0 and len(score) >= a.min: break
    for k, u in enumerate(U):
        if k not in score and test(u): score[k] = s
tiers = collections.Counter(score.values())
print(f"intent: layer={a.layer} category={a.cat} verb={a.verb}  ->  {len(score)} units; by step: " + ', '.join(f'{lab}={tiers[s]}' for s, lab, _ in STEPS if tiers[s]))

def table(title, idx):
    xs = [U[k] for k in idx]
    if not xs: return
    c = collections.Counter(u['style'] for u in xs)
    print(f"\n{title} (n={len(xs)})")
    for st, n in c.most_common():
        g = [u for u in xs if u['style'] == st]
        ex = sorted((u for u in g if 8 <= u['loc'] <= 60), key=lambda u: (u['cyc'], u['loc']))
        e = ex[0] if ex else g[0]
        print(f"  {n / len(xs):5.0%}  {st:38s} median loc {statistics.median(u['loc'] for u in g):>4}  cyc {statistics.median(u['cyc'] for u in g):>4}  "
              f"async {sum(u['async'] for u in g) / len(g):.0%}  e.g. {e['file'].split('/src/')[-1]}:{e['line']} {e['cls'] or ''}.{e['name']}")

same = [k for k in score if a.layer and U[k]['layer'] == a.layer]
other = [k for k in score if k not in set(same)]
if a.layer:
    table(f'in {a.layer}', same)
    table('elsewhere in the code base', other)
    seen_here = {U[k]['style'] for k in same}
    only_elsewhere = collections.Counter(U[k]['style'] for k in other if U[k]['style'] not in seen_here)
    if only_elsewhere:
        print('\nstyles used for this intent elsewhere but not in this layer: ' + ', '.join(f'{s} ({n})' for s, n in only_elsewhere.most_common()))
else:
    table('all layers', list(score))
