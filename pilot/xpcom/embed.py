import json, sys, numpy as np, torch
from transformers import AutoTokenizer, AutoModel
torch.set_num_threads(4)
V = json.load(open('variants.json'))['texts']; which = sys.argv[1]
if which == 'unixcoder':
    tok = AutoTokenizer.from_pretrained('microsoft/unixcoder-base'); m = AutoModel.from_pretrained('microsoft/unixcoder-base').eval()
    def enc(b):
        h = m(**b).last_hidden_state; mk = b['attention_mask'].unsqueeze(-1).float(); return (h * mk).sum(1) / mk.sum(1)
else:
    tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B', padding_side='left'); m = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', dtype=torch.float32).eval()
    def enc(b): return m(**b).last_hidden_state[:, -1]
out = {}
for k, texts in V.items():
    Z = []
    for i in range(0, len(texts), 8):
        b = tok(texts[i:i + 8], padding=True, truncation=True, max_length=256, return_tensors='pt')
        with torch.no_grad(): Z.append(torch.nn.functional.normalize(enc(b), dim=1).numpy())
    out[k] = np.vstack(Z); print(which, k, out[k].shape, flush=True)
np.savez(f'emb_{which}.npz', **out)
