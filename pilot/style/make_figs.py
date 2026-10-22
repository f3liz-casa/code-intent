import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
model, var = sys.argv[1], sys.argv[2]
D = json.load(open('texts.json')); items = D['items']
dsi = [i for i, x in enumerate(items) if x['kind'] == 'dataset']; rli = [i for i, x in enumerate(items) if x['kind'] == 'real']
E = np.load(f'emb_{model}.npz')[var]; Zd, Zr = E[dsi], E[rli]
ds = [items[i] for i in dsi]; rl = [items[i] for i in rli]
S = ['P', 'O', 'F', 'D', 'G']; SN = {'P': 'procedural', 'O': 'object-oriented', 'F': 'functional', 'D': 'data-oriented', 'G': 'declarative idiom'}
SUBS = ['numeric', 'collections', 'logic', 'filesystem', 'network', 'compose']
SC = {'P': '#0072B2', 'O': '#E69F00', 'F': '#009E73', 'D': '#D55E00', 'G': '#CC79A7'}
SUBC = dict(zip(SUBS, ['#0072B2', '#56B4E9', '#009E73', '#E69F00', '#D55E00', '#7F7F7F']))
intents = list(dict.fromkeys(x['intent'] for x in ds)); isub = {x['intent']: x['sub'] for x in ds}
order = sorted(intents, key=lambda i: (SUBS.index(isub[i]), i))
idx = {(x['intent'], x['style']): k for k, x in enumerate(ds)}
G = np.stack([[Zd[idx[(i, s)]] for s in S] for i in order])          # nI x 5 x d
fig, ax = plt.subplots(1, 3, figsize=(19, 6.2), gridspec_kw=dict(width_ratios=[1.05, 1, 1]))
# (a) cell-to-cell cosine, rows ordered by category then style
cells = G.reshape(-1, G.shape[-1]); Cm = cells @ cells.T
im = ax[0].imshow(Cm, cmap='viridis'); ax[0].set_title('(a) cosine between all 100 cells\nblocks = same intent, band structure = category', fontsize=10)
b = np.cumsum([0] + [sum(1 for i in order if isub[i] == s) * 5 for s in SUBS])
for k in range(len(SUBS)):
    ax[0].plot([b[k] - .5, b[k + 1] - .5], [b[k] - .5, b[k] - .5], c='w', lw=1); ax[0].plot([b[k] - .5, b[k] - .5], [b[k] - .5, b[k + 1] - .5], c='w', lw=1)
    ax[0].text(-3, (b[k] + b[k + 1]) / 2, SUBS[k], ha='right', va='center', fontsize=8)
ax[0].set_xticks([]); ax[0].set_yticks([]); plt.colorbar(im, ax=ax[0], fraction=.046)
# (b) category space: PCs of intent means (style averaged)
A = G.mean(1); A0 = A - A.mean(0); U, sv, Vt = np.linalg.svd(A0, full_matrices=False); P2 = Vt[:2]
mk = {'P': 'o', 'O': 's', 'F': '^', 'D': 'D', 'G': 'v'}
for ii, i in enumerate(order):
    for si, s in enumerate(S):
        p = P2 @ (G[ii, si] - A.mean(0)); ax[1].scatter(*p, c=SUBC[isub[i]], marker=mk[s], s=26, alpha=.85, edgecolors='none')
    p = P2 @ A0[ii]; ax[1].annotate(i, p, fontsize=6, alpha=.7)
ax[1].set_title('(b) category space (top-2 PCs of intent means)\ncolour = sub-category, marker = style', fontsize=10)
for s in SUBS: ax[1].scatter([], [], c=SUBC[s], label=s, s=26)
for s in S: ax[1].scatter([], [], c='k', marker=mk[s], label=SN[s], s=26)
ax[1].legend(fontsize=6.5, ncol=2, loc='best'); ax[1].set_xticks([]); ax[1].set_yticks([])
# (c) style space: learned from same-intent offsets; category centroid removed
Xc = G - G.mean(1, keepdims=True); V = Xc.mean(0); Vc = V - V.mean(0); B = np.linalg.svd(Vc, full_matrices=False)[2][:4]
topc = {t: G[[k for k, i in enumerate(order) if next(x['top'] for x in ds if x['intent'] == i) == t]].mean((0, 1)) for t in ['compute', 'io', 'glue']}
for ii, i in enumerate(order):
    t = next(x['top'] for x in ds if x['intent'] == i)
    for si, s in enumerate(S):
        c = B @ (G[ii, si] - topc[t]); ax[2].scatter(c[0], c[1], c=SC[s], s=16, alpha=.55, edgecolors='none')
for si, s in enumerate(S):
    c = B @ V[si]; ax[2].scatter(c[0], c[1], c=SC[s], s=170, marker='*', edgecolors='k', linewidths=.6, label=SN[s] + ' (offset)')
CORP = {'statistics': 'k', 'numpy_lib': 'k', 'stdlib_fs': 'k', 'collections': 'k'}
cn = sorted({x['corpus'] for x in rl})
for c in cn:
    r = [k for k, x in enumerate(rl) if x['corpus'] == c]
    tc = topc['compute']  # real code: use nearest top centroid
    pts = []
    for k in r:
        t = max(topc, key=lambda t_: Zr[k] @ topc[t_] / np.linalg.norm(topc[t_])); pts.append(B @ (Zr[k] - topc[t]))
    m = np.mean(pts, 0); ax[2].scatter(m[0], m[1], marker='X', s=90, c='white', edgecolors='k', linewidths=1.2); ax[2].annotate(c, (m[0], m[1]), fontsize=7, xytext=(4, 4), textcoords='offset points')
ax[2].set_title('(c) style space (4-d, shown PC1/PC2)\nstars = learned style offsets; white X = real-code corpus centroids', fontsize=10)
ax[2].legend(fontsize=6.5, loc='best'); ax[2].set_xticks([]); ax[2].set_yticks([])
fig.suptitle(f'{model} / {var} identifiers', fontsize=11); fig.tight_layout()
fig.savefig(f'out/fig_{model}_{var}.png', dpi=130); print('saved')
