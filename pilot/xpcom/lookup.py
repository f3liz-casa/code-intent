"""Query the XPCOM bridge index:  python3 lookup.py <methodName>   -> declaring interface(s), C++ implementing classes (file:line), JS call-site count."""
import json, sys, collections
I = json.load(open('index.json'))
def lookup(m):
    out = []
    for i in I['methods'].get(m, []):
        d = I['interfaces'][i]; impl = I['impls'].get(i, {}).get(m, [])
        out.append(dict(interface=i, idl=d['file'], base=d['base'], implementations=[f"{x['cls']} ({x['file']}:{x['line']})" for x in impl]))
    return out
if __name__ == '__main__':
    for m in sys.argv[1:]: print(m, json.dumps(lookup(m), indent=1))
