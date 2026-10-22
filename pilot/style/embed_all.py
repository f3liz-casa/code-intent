import json, sys, numpy as np, torch
from transformers import AutoTokenizer, AutoModel
torch.set_num_threads(4)
D = json.load(open('texts.json')); items = D['items']; desc = D['desc']
raw = [x['raw'] for x in items]; hs = [x['hashed'] for x in items]; dtx = list(desc.values())
def run(name, tok, enc, ML=256, bs=8):
    out = {}
    for tag, texts in (('raw', raw), ('hashed', hs), ('desc', dtx)):
        Z = []
        for i in range(0, len(texts), bs):
            b = tok(texts[i:i+bs], padding=True, truncation=True, max_length=ML, return_tensors='pt')
            with torch.no_grad(): Z.append(torch.nn.functional.normalize(enc(b), dim=1).numpy())
        out[tag] = np.vstack(Z); print(name, tag, out[tag].shape, flush=True)
    np.savez(f'emb_{name}.npz', **out)
which = sys.argv[1]
if which == 'unixcoder':
    tok = AutoTokenizer.from_pretrained('microsoft/unixcoder-base'); m = AutoModel.from_pretrained('microsoft/unixcoder-base').eval()
    def enc(b):
        h = m(**b).last_hidden_state; mk = b['attention_mask'].unsqueeze(-1).float(); return (h*mk).sum(1)/mk.sum(1)
    run('unixcoder', tok, enc)
else:
    tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B', padding_side='left')
    m = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', torch_dtype=torch.float32).eval()
    if which == 'qwen3_lora':
        from peft import LoraConfig, get_peft_model
        m = get_peft_model(m, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=['q_proj','k_proj','v_proj','o_proj']))
        sd = torch.load('../qwen3_lora.pt', map_location='cpu')
        r = m.load_state_dict(sd, strict=False)
        assert not [k for k in sd if k in r.unexpected_keys], r.unexpected_keys[:3]
        print('loaded lora tensors', len(sd), 'unexpected', len(r.unexpected_keys)); m.eval()
    def enc(b): return m(**b).last_hidden_state[:, -1]
    run(which, tok, enc)
