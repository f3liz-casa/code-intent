import json, random, re, time, sys, hashlib, numpy as np, torch
from collections import defaultdict
from transformers import AutoTokenizer, AutoModel
from peft import LoraConfig, get_peft_model
random.seed(0); torch.manual_seed(0); torch.set_num_threads(4)
D=json.load(open('/tmp/w/s2/pairs.json'))
def cap(v,per,n):
    random.shuffle(v); c=defaultdict(int); o=[]
    for x in v:
        if c[x['file']]<per: c[x['file']]+=1; o.append(x)
    return o[:n]
train=[]
for k,per,n in [('sqlite',4,500),('ff-dom',4,250),('ff-netwerk',4,100),('ff-toolkit',4,200),('ff-browser',3,250)]:
    train+=cap(D[k],per,n)
random.shuffle(train); print('train pairs',len(train),flush=True)
# ---- alien code
KW={'if':'kel','else':'nor','for':'loop','while':'spin','return':'yield','break':'halt','continue':'skip','int':'num','char':'glyph',
    'void':'nil','static':'fixed','struct':'clump','const':'keep','unsigned':'natural','switch':'fork','case':'when','NULL':'VOID'}
OPS=[('==',' isq '),('!=',' nsq '),('&&',' and_ '),('||',' or_ '),('->',' of '),('{',' begin~ '),('}',' ~end '),(';',' . ')]
def zorb(code,obf=False):
    names={}
    def kw(m):
        w=m.group(0)
        if w in KW: return KW[w]
        if obf and not w.isupper() and len(w)>2:
            if w not in names: names[w]='q'+hashlib.md5(w.encode()).hexdigest()[:5]
            return names[w]
        return w
    s=re.sub(r'[A-Za-z_][A-Za-z_0-9]*',kw,code)
    for a,b in OPS: s=s.replace(a,b)
    return re.sub(r'[ \t]+',' ',s)
qj=cap(D['quickjs'],5,200); ju=cap(D['julia'],4,200); pa=D['pandoc'][:46]
EV={'quickjs (C, unseen repo)':qj,'julia (unseen language)':ju,'pandoc (Haskell, unseen language)':pa,
    'quickjs in made-up syntax "zorb"':[dict(x,code=zorb(x['code'])) for x in qj],
    'quickjs zorb + obfuscated names':[dict(x,code=zorb(x['code'],True)) for x in qj]}
# ---- model
MN='Qwen/Qwen3-Embedding-0.6B'
tok=AutoTokenizer.from_pretrained(MN,padding_side='left'); base=AutoModel.from_pretrained(MN,dtype=torch.float32)
INS='Instruct: Given a description of a function, retrieve the source code that implements it\nQuery:'
def enc(m,texts,ml):
    b=tok(texts,padding=True,truncation=True,max_length=ml,return_tensors='pt')
    h=m(**b).last_hidden_state[:,-1]; return torch.nn.functional.normalize(h,dim=1)
@torch.no_grad()
def embed(m,texts,ml,bs=16):
    m.eval(); order=sorted(range(len(texts)),key=lambda i:len(texts[i])); out=[None]*len(texts)
    for i in range(0,len(order),bs):
        idx=order[i:i+bs]; e=enc(m,[texts[j] for j in idx],ml)
        for j,r in zip(idx,e): out[j]=r.numpy()
    return np.vstack(out)
def evaluate(m,tag):
    t0=time.time(); res={}; qcache={}
    for name,items in EV.items():
        qs=[INS+x['query'] for x in items]; key=tuple(qs)
        if key not in qcache: qcache[key]=embed(m,qs,96)
        Q=qcache[key]; C=embed(m,[x['code'] for x in items],192)
        S=Q@C.T; rank=(S>np.diag(S)[:,None]).sum(1)+1
        res[name]=dict(n=len(items),mrr=float((1/rank).mean()),r1=float((rank==1).mean()),r10=float((rank<=10).mean()),
            finite=bool(np.isfinite(C).all()),mean_cos_between_codes=float((C@C.T).mean()))
        res[name]['_C']=C
        print(tag,name,{k:round(v,3) if isinstance(v,float) else v for k,v in res[name].items() if k!='_C'},flush=True)
    # invariance: original quickjs fn vs its zorb version
    a=res['quickjs (C, unseen repo)']['_C']; z=res['quickjs in made-up syntax "zorb"']['_C']; o=res['quickjs zorb + obfuscated names']['_C']
    for nm,x in [('zorb',z),('zorb+obf',o)]:
        S=a@x.T; rk=(S>np.diag(S)[:,None]).sum(1)+1
        res['match original->'+nm]=dict(n=len(a),r1=float((rk==1).mean()),r10=float((rk<=10).mean()),mean_cos_pair=float(np.diag(S).mean()))
        print(tag,'original->'+nm,res['match original->'+nm],flush=True)
    for v in res.values(): v.pop('_C',None)
    print(tag,'eval secs',time.time()-t0,flush=True); return res
out={}
out=json.load(open('/tmp/w/s2/ft_results.json')); assert 'before' in out
cfg=LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,target_modules=['q_proj','k_proj','v_proj','o_proj'])
base.gradient_checkpointing_enable(); base.enable_input_require_grads(); base.config.use_cache=False
m=get_peft_model(base,cfg); m.print_trainable_parameters()
opt=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=2e-4,weight_decay=0.0)
BS=16; steps=len(train)//BS; sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda s:min(1,(s+1)/8)*max(0.05,1-s/steps))
t0=time.time()
for s in range(steps):
    b=train[s*BS:(s+1)*BS]; m.train()
    q=enc(m,[INS+x['query'] for x in b],96); c=enc(m,[x['code'] for x in b],160)
    S=q@c.T/0.05; y=torch.arange(len(b))
    loss=(torch.nn.functional.cross_entropy(S,y)+torch.nn.functional.cross_entropy(S.T,y))/2
    opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    print(f'step {s+1}/{steps} loss {loss.item():.3f} elapsed {time.time()-t0:.0f}s',flush=True)
try: m.save_pretrained('/tmp/w/s2/lora_adapter')
except Exception as e: print('save failed',e,flush=True); torch.save({k:v for k,v in m.state_dict().items() if 'lora' in k},'/tmp/w/s2/lora.pt')
out['train']=dict(pairs=steps*BS,steps=steps,secs=time.time()-t0)
out['after']=evaluate(m,'AFTER'); json.dump(out,open('/tmp/w/s2/ft_results.json','w'),indent=1)
print('DONE')
