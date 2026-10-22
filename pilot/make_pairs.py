import os, re, json, random, sys
sys.path.insert(0,'/tmp/w/s')
from chunklib import LANGS, COMMENT, walk
from tree_sitter import Language, Parser
R='/tmp/w/repos/'
def clean_comment(t):
    t=re.sub(r'^\s*(/\*+|//+!?|#+|--\s*\|?|\{-\|?)','',t,flags=re.M)
    t=re.sub(r'(\*+/|-\})\s*$','',t.strip())
    t=re.sub(r'^\s*\*+ ?','',t,flags=re.M)
    return re.sub(r'\s+',' ',t).strip()
def extract(root,lang,limit=None):
    ts,kinds,exts=LANGS[lang]; p=Parser(Language(ts)); out=[]
    for dp,_,fs in os.walk(root):
        if '/.git' in dp: continue
        for f in sorted(fs):
            if os.path.splitext(f)[1] not in exts: continue
            path=os.path.join(dp,f)
            try: src=open(path,'rb').read()
            except OSError: continue
            if len(src)>500_000: continue
            t=p.parse(src)
            for n in walk(t.root_node):
                if n.type not in kinds: continue
                prev=n.prev_sibling
                if prev is None or prev.type not in COMMENT: continue
                if n.start_point[0]-prev.end_point[0]>1: continue
                # merge consecutive line comments
                cs=[prev]
                while cs[0].prev_sibling is not None and cs[0].prev_sibling.type in COMMENT and cs[0].start_point[0]-cs[0].prev_sibling.end_point[0]<=1: cs.insert(0,cs[0].prev_sibling)
                q=clean_comment(' '.join(src[c.start_byte:c.end_byte].decode('utf8','ignore') for c in cs))
                if len(q.split())<6 or len(q)>600 or re.search(r'copyright|license|\bmpl\b',q,re.I): continue
                # code without inner comments
                rng=sorted((c.start_byte,c.end_byte) for c in walk(n) if c.type in COMMENT)
                body=bytearray(); pos=n.start_byte
                for a,b in rng: body+=src[pos:a]; pos=b
                body+=src[pos:n.end_byte]
                code=body.decode('utf8','ignore')
                nl=code.count('\n')+1
                if nl<4 or nl>120: continue
                out.append(dict(file=os.path.relpath(path,root),query=q,code=code))
    return out
if __name__=='__main__':
    spec=[('sqlite','sqlite','c'),('ff-dom','firefox/dom/base','cpp'),('ff-netwerk','firefox/netwerk/protocol/http','cpp'),
          ('ff-toolkit','firefox/toolkit/modules','js'),('ff-browser','firefox/browser/components','js'),
          ('quickjs','quickjs','c'),('lavandula','lavandula','c'),('julia','julia','julia'),('pandoc','pandoc','haskell')]
    res={}
    for name,path,lang in spec:
        res[name]=extract(R+path,lang); print(name,len(res[name]),flush=True)
    json.dump(res,open('/tmp/w/s2/pairs.json','w'))
