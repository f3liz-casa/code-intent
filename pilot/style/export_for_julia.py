"""Dump embeddings + labels as plain TSV for the Julia matrix analysis (Julia pkg server is blocked here, so stdlib only)."""
import json, numpy as np, os
D = json.load(open('texts.json')); items = D['items']
ds = [x for x in items if x['kind'] == 'dataset']; rl = [x for x in items if x['kind'] == 'real']
dsi = [i for i, x in enumerate(items) if x['kind'] == 'dataset']; rli = [i for i, x in enumerate(items) if x['kind'] == 'real']
with open('jl/meta_ds.tsv', 'w') as f:
    for x in ds: f.write('\t'.join([x['intent'], x['top'], x['sub'], x['style']]) + '\n')
with open('jl/meta_real.tsv', 'w') as f:
    for x in rl: f.write('\t'.join([x['corpus'], x['top'] or '-', x['sub'] or '-', x['name']]) + '\n')
with open('jl/meta_desc.tsv', 'w') as f:
    for k in D['desc']: f.write(k + '\n')
for m in ['unixcoder', 'qwen3', 'qwen3_lora']:
    if not os.path.exists(f'emb_{m}.npz'): continue
    E = np.load(f'emb_{m}.npz')
    for v in ['raw', 'hashed']:
        np.savetxt(f'jl/{m}_{v}_ds.tsv', E[v][dsi], delimiter='\t', fmt='%.6g')
        np.savetxt(f'jl/{m}_{v}_real.tsv', E[v][rli], delimiter='\t', fmt='%.6g')
    np.savetxt(f'jl/{m}_desc.tsv', E['desc'], delimiter='\t', fmt='%.6g')
print('exported')
