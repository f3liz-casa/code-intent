from dataset import S, STYLES
TESTS={
'word_count':[("The cat the dog THE end",)],
'total_price':[([(2.0,3),(1.5,2)],0.1)],
'adult_names':[([{"name":"a","age":20},{"name":"b","age":5},{"name":"c","age":18}],)],
'moving_average':[([1,2,3,4,5,6],3)],
'balanced':[("([]{})",),("([)]",),("((",),("a(b)c",)],
'flatten':[([1,[2,[3,[4]],5],[],6],)],
'group_by':[([{"t":"x","v":1},{"t":"y","v":2},{"t":"x","v":3}],"t")],
'normalize':[([3,5,9,13],)],
'fib':[(10,),(1,),(2,)],
'dedupe':[([3,1,3,2,1,4],)],
'top_k':[({"a":3,"b":9,"c":5,"d":1},2)],
'balance':[(100,[("deposit",50),("withdraw",30)])],
}
bad=0
for it,cases in TESTS.items():
    for args in cases:
        ref=None
        for st in STYLES:
            code,call=S[it][st]; ns={}
            exec(code,ns)
            try: r=eval(call,{**ns,'args':args})
            except Exception as e: r=('ERR',repr(e))
            if hasattr(r,'tolist'): r=r.tolist()
            if ref is None: ref=r
            elif r!=ref and not (isinstance(r,list) and isinstance(ref,list) and len(r)==len(ref) and all(abs(a-b)<1e-9 for a,b in zip(r,ref))) and not (isinstance(r,float) and abs(r-ref)<1e-9):
                bad+=1; print('MISMATCH',it,st,args,r,ref)
print('bad',bad)
# error-path for balance
for st in STYLES:
    code,call=S['balance'][st]; ns={}; exec(code,ns)
    try: eval(call,{**ns,'args':(10,[("withdraw",50)])}); print('no raise',st)
    except ValueError: pass
