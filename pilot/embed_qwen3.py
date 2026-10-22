import sys, json, random, collections, numpy as np, torch
sys.path.insert(0,'/tmp/w/s')
from chunklib import chunks, toks
from transformers import AutoTokenizer, AutoModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
R='/tmp/w/repos/'
# name, path, lang, group, language-family
CORP=[('sqlite',R+'sqlite','c','clear','C'),('quickjs',R+'quickjs','c','clear','C'),
('lavandula',R+'lavandula','c','clear','C'),
('ff-netwerk-http',R+'firefox/netwerk/protocol/http','cpp','drifted','C++'),
('ff-dom-base',R+'firefox/dom/base','cpp','drifted','C++'),
('ff-toolkit-js',R+'firefox/toolkit/modules','js','drifted','JS'),
('ff-browser-js',R+'firefox/browser/components','js','drifted','JS'),
('julia',R+'julia','julia','clear','Julia'),('pandoc',R+'pandoc','haskell','clear','Haskell')]
random.seed(0); torch.manual_seed(0); torch.set_num_threads(4)
tok=AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B',padding_side='left'); mdl=AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B',torch_dtype=torch.float32).eval()
def embed(texts,bs=16):
    out=[]
    for i in range(0,len(texts),bs):
        b=tok(texts[i:i+bs],padding=True,truncation=True,max_length=256,return_tensors='pt')
        with torch.no_grad(): h=mdl(**b).last_hidden_state
        e=h[:,-1]
        out.append(torch.nn.functional.normalize(e,dim=1).numpy())
    return np.vstack(out)
def sample(cs,nfiles=60,per=12):
    byf=collections.defaultdict(list)
    for c in cs: byf[c['file']].append(c)
    fs=[f for f,v in byf.items() if len(v)>=4]; random.shuffle(fs); fs=fs[:nfiles]
    return [c for f in fs for c in random.sample(byf[f],min(per,len(byf[f])))]
def stats(Z,files):
    files=np.array(files); S=Z@Z.T; n=len(Z)
    same=(files[:,None]==files[None,:]); np.fill_diagonal(same,False)
    diff=files[:,None]!=files[None,:]
    w=S[same].mean(); a=S[diff].mean()
    # kNN same-file precision @5
    S2=S.copy(); np.fill_diagonal(S2,-9); nn=np.argsort(-S2,1)[:,:5]
    p5=np.mean([(files[nn[i]]==files[i]).mean() for i in range(n)])
    # chance for p5
    cnt=collections.Counter(files); chance=np.mean([(cnt[f]-1)/(n-1) for f in files])
    return dict(within=float(w),across=float(a),lift=float(w-a),knn5=float(p5),knn5_chance=float(chance),
                knn5_over_chance=float(p5/chance))
res={}; allc=[]
for name,path,lang,grp,fam in CORP:
    cs=sample(chunks(path,lang)); print(name,len(cs),flush=True)
    for c in cs: c['corp']=name
    allc+=cs
texts=[c['text'] for c in allc]
import time;t0=time.time();E=embed(texts);print('embed secs',time.time()-t0,flush=True)
vec=TfidfVectorizer(tokenizer=toks,lowercase=False,token_pattern=None,min_df=3,max_features=30000)
X=vec.fit_transform(texts); T=TruncatedSVD(64,random_state=0).fit_transform(X); T/=np.linalg.norm(T,axis=1,keepdims=True)+1e-9
for name,path,lang,grp,fam in CORP:
    idx=[i for i,c in enumerate(allc) if c['corp']==name]
    files=[allc[i]['file'] for i in idx]
    res[name]=dict(group=grp,family=fam,n=len(idx),nfiles=len(set(files)),
        qwen3=stats(E[idx],files),tfidf=stats(T[idx],files))
json.dump(res,open('/tmp/w/s/results_qwen.json','w'),indent=1)
print(json.dumps(res,indent=1))
