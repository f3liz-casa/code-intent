"""Baseline pilot: function-level chunks, style metrics, TF-IDF+SVD embeddings.
NOT a neural embedding. Placeholder until a pretrained code model is reachable.
Usage: python3 baseline.py name=path=lang [name=path=lang ...]   lang: c|cpp|julia|haskell|js
"""
import sys, re, json, os, collections
import numpy as np
from tree_sitter import Language, Parser
import tree_sitter_c, tree_sitter_cpp, tree_sitter_julia, tree_sitter_haskell, tree_sitter_javascript
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

LANGS = {
 'c':   (tree_sitter_c.language(),   {'function_definition'}, {'.c','.h'}),
 'cpp': (tree_sitter_cpp.language(), {'function_definition'}, {'.cpp','.cc','.h'}),
 'julia': (tree_sitter_julia.language(), {'function_definition'}, {'.jl'}),
 'haskell': (tree_sitter_haskell.language(), {'function'}, {'.hs'}),
 'js': (tree_sitter_javascript.language(), {'function_declaration','method_definition'}, {'.js','.mjs','.jsm'}),
}
COMMENT = {'comment','block_comment','line_comment'}
NEST = {'if_statement','for_statement','while_statement','switch_statement','for_range_loop',
        'if_expression','for_statement','while_statement','try_statement','do_statement'}

def walk(n):
    st=[n]
    while st:
        x=st.pop(); yield x; st.extend(x.children)

def depth(n):
    best=0; st=[(n,0)]
    while st:
        x,d=st.pop(); best=max(best,d)
        for c in x.children: st.append((c,d+(1 if c.type in NEST else 0)))
    return best

def chunks(root, lang):
    ts_lang, kinds, exts = LANGS[lang]
    p = Parser(Language(ts_lang)); out=[]
    for dp,_,fs in os.walk(root):
        if '/.git' in dp: continue
        for f in fs:
            if os.path.splitext(f)[1] not in exts: continue
            path=os.path.join(dp,f)
            try: src=open(path,'rb').read()
            except OSError: continue
            if len(src)>500_000: continue
            t=p.parse(src)
            for n in walk(t.root_node):
                if n.type in kinds:
                    body=src[n.start_byte:n.end_byte].decode('utf8','ignore')
                    nl=body.count('\n')+1
                    if nl<4: continue
                    com=sum(1 for c in walk(n) if c.type in COMMENT)
                    prev=n.prev_named_sibling
                    pre=1 if prev is not None and prev.type in COMMENT else 0
                    out.append(dict(file=os.path.relpath(path,root),lines=nl,
                                    comments=com,doc=pre,nest=depth(n),text=body))
    return out

def toks(s):
    s=re.sub(r'([a-z])([A-Z])',r'\1 \2',s)
    return [w.lower() for w in re.findall(r'[A-Za-z]{3,}',s)]

def main():
    sets={}
    for a in sys.argv[1:]:
        name,path,lang=a.split('=')
        sets[name]=chunks(path,lang); print(name,len(sets[name]),'functions',file=sys.stderr)
    allc=[(k,c) for k,v in sets.items() for c in v]
    vec=TfidfVectorizer(tokenizer=toks,lowercase=False,token_pattern=None,min_df=3,max_features=30000)
    X=vec.fit_transform([c['text'] for _,c in allc])
    Z=TruncatedSVD(64,random_state=0).fit_transform(X)
    Z/=np.linalg.norm(Z,axis=1,keepdims=True)+1e-9
    rows=collections.defaultdict(list)
    for (k,c),z in zip(allc,Z): rows[k].append((c,z))
    res={}
    for k,v in rows.items():
        L=np.array([c['lines'] for c,_ in v]); C=np.array([c['comments'] for c,_ in v])
        D=np.array([c['doc'] for c,_ in v]); N=np.array([c['nest'] for c,_ in v])
        byf=collections.defaultdict(list)
        for c,z in v: byf[c['file']].append(z)
        coh=[]
        for f,zs in byf.items():
            if len(zs)>=3:
                M=np.array(zs); S=M@M.T; n=len(zs)
                coh.append((S.sum()-n)/(n*(n-1)))
        res[k]=dict(functions=len(v),median_lines=float(np.median(L)),p90_lines=float(np.percentile(L,90)),
            comment_per_100_lines=float(100*C.sum()/L.sum()),doc_comment_share=float(D.mean()),
            mean_max_nesting=float(N.mean()),files_with_3plus_funcs=len(coh),
            within_file_cohesion=float(np.mean(coh)) if coh else None)
    print(json.dumps(res,indent=1))
main()
