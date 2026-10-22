import json, numpy as np, torch
from transformers import AutoTokenizer, AutoModel
torch.set_num_threads(4)
D = json.load(open('eval_sites.json')); sites = [e['masked'] for e in D['eval']]; names = list(D['itexts']); itx = [D['itexts'][n] for n in names]
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B', padding_side='left'); m = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', dtype=torch.float32).eval()
def emb(texts):
    Z = []
    for i in range(0, len(texts), 8):
        b = tok(texts[i:i + 8], padding=True, truncation=True, max_length=256, return_tensors='pt')
        with torch.no_grad(): Z.append(torch.nn.functional.normalize(m(**b).last_hidden_state[:, -1], dim=1).numpy())
        if i % 80 == 0: print(i, len(texts), flush=True)
    return np.vstack(Z)
np.savez('emb_index.npz', sites=emb(sites), ifaces=emb(itx), names=np.array(names))
print('done')
