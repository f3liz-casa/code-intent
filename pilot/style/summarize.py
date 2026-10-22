import re, sys
def parse(path):
    root = {}; stack = [(-1, root)]
    for line in open(path):
        ind = (len(line) - len(line.lstrip())) // 2; k, _, v = line.strip().partition(':'); v = v.strip()
        while stack[-1][0] >= ind: stack.pop()
        if v == '': d = {}; stack[-1][1][k] = d; stack.append((ind, d))
        else:
            if v.startswith('('): v = tuple(float(x) for x in v.strip('()').split(','))
            else:
                try: v = float(v)
                except ValueError: pass
            stack[-1][1][k] = v
    return root
M = ['unixcoder', 'qwen3', 'qwen3_lora', 'asttok']; V = ['raw', 'hashed']
R = {(m, v): parse(f'out/{m}_{v}.txt') for m in M for v in V}
def row(f): return ' | '.join(f(R[(m, v)]) for m in M for v in V)
hdr = '| ' + ' | '.join(f'{m} {v}' for m in M for v in V)
print('MODELS:', hdr)
print('variance shares (top / sub|top / intent|sub / style / interaction)')
for k in ['top_category', 'sub_given_top', 'intent_given_sub', 'style', 'interaction']: print(k, row(lambda r: '%.2f' % r['variance'][k]))
print('top-cat LOIO acc (obs, perm-mean, p) chance~0.43'); print(row(lambda r: '%.2f/%.2f/%.3f' % r['top_acc']))
print('sub-cat LOIO'); print(row(lambda r: '%.2f/%.2f/%.3f' % r['sub_acc']))
print('style acc', ); 
for k in ['global', 'intent_centered', 'true_sub', 'pred_sub']: print(k, row(lambda r: '%.2f' % r['style_acc'][k]))
print('analogy'); 
for k in ['same_sub', 'other_top', 'all']: print(k, row(lambda r: '%.2f' % r['analogy_row_acc'][k]))
print('style vec cos between tops'); 
for k in R[('qwen3', 'raw')]['style_vec_cos_between_tops']: print(k, row(lambda r: '%.2f' % r['style_vec_cos_between_tops'][k]))
C = ['statistics', 'numpy_lib', 'networkx_paths', 'collections', 'argparse', 'stdlib_fs', 'stdlib_net']
print('real top_acc'); 
for c in C: print(c, row(lambda r: '%.2f' % r['real'][c]['top_acc'] if 'top_acc' in r['real'][c] else '-'))
print('real sub_acc')
for c in C: print(c, row(lambda r: '%.2f' % r['real'][c]['sub_acc'] if 'sub_acc' in r['real'][c] else '-'))
print('outlier auroc')
for c in C: print(c, row(lambda r: '%.2f' % r['real'][c]['outlier_auroc']))
print('spread')
for c in C: print(c, row(lambda r: '%.3f' % r['real'][c]['spread']))
print('style share P/O/F/D/G (qwen3 raw, qwen3 hashed, unixcoder raw)')
for m, v in [('qwen3', 'raw'), ('qwen3', 'hashed'), ('unixcoder', 'raw')]:
    print(m, v)
    for c in C: print('  ', c.ljust(15), ' '.join('%s%.2f' % (s, R[(m, v)]['real'][c]['style_share'][s]) for s in 'POFDG'))
