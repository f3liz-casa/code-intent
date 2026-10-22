"""Export the raw material from which Intent / category are *derived* (no hand-written leaf table, no hand categories):
callee tokens (receiver head + method, or bare function) and the words of the unit's name, as sparse unit-token counts.

usage: python3 -I export_tokens.py <extract dir with units.jsonl> <out dir (same as export_intent_style.py)> [--min-df 5]
Writes tokens_sparse.tsv (unit index starting at 1, token index starting at 1, count) and tokens_vocab.txt.
Unit order is units.jsonl restricted to loc >= 3, the same as export_intent_style.py."""
import json, re, sys, collections

src, out = sys.argv[1:3]
min_df = int(sys.argv[sys.argv.index('--min-df') + 1]) if '--min-df' in sys.argv else 5
U = [u for u in map(json.loads, open(f'{src}/units.jsonl')) if u['loc'] >= 3]
WORD = re.compile(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+')

def tokens(u):
    t = []
    for c in u['callees']:
        c = re.sub(r'^this\.', '', c).replace('?.', '.')
        parts = c.split('.')
        if len(parts) == 1: t.append('f:' + parts[0])
        else:
            t.append('c:' + parts[0] + '.' + parts[-1])   # receiver head + method, e.g. usersRepository.findOneBy
            t.append('m:' + parts[-1])                    # method alone, e.g. findOneBy
    t += ['n:' + w.lower() for w in WORD.findall(u['name'] or '')]   # words of the unit's own name
    return t

T = [tokens(u) for u in U]
df = collections.Counter(w for ts in T for w in set(ts))
vocab = [w for w, c in df.most_common() if c >= min_df]
vi = {w: i + 1 for i, w in enumerate(vocab)}
with open(f'{out}/tokens_sparse.tsv', 'w') as f:
    for i, ts in enumerate(T, 1):
        for w, c in collections.Counter(w for w in ts if w in vi).items(): f.write(f'{i}\t{vi[w]}\t{c}\n')
with open(f'{out}/tokens_vocab.txt', 'w') as f: f.write('\n'.join(vocab) + '\n')
print(len(U), 'units', len(vocab), 'tokens (df >=', min_df, ')')
