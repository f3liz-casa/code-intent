"""Same-intent functions in five styles (Python), hand-written; behavior checked by TESTS.

Styles: P procedural, O object-oriented, F functional (reduce/map/recursion, no mutation),
D data-oriented (flat columns, numpy batches), G declarative idiom (comprehensions / stdlib one-liners).
Each snippet defines the text that gets embedded (`code`); `call` is an adapter that is NOT embedded,
used only to run the shared test for that intent.
"""
import numpy as np

S = {}  # S[intent][style] = (code, call_expr_template)  call: python expr using `args`

def add(intent, style, code, call):
    S.setdefault(intent, {})[style] = (code.strip('\n'), call)

# ---- 1 word_count -------------------------------------------------------
add('word_count','P','''
def count_words(text):
    counts = {}
    for word in text.lower().split():
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1
    return counts
''','count_words(*args)')
add('word_count','O','''
class WordCounter:
    def __init__(self):
        self.counts = {}

    def add(self, word):
        self.counts[word] = self.counts.get(word, 0) + 1

    def feed(self, text):
        for word in text.lower().split():
            self.add(word)
        return self

    def result(self):
        return dict(self.counts)
''','WordCounter().feed(*args).result()')
add('word_count','F','''
from functools import reduce

def count_words(text):
    bump = lambda acc, w: {**acc, w: acc.get(w, 0) + 1}
    return reduce(bump, text.lower().split(), {})
''','count_words(*args)')
add('word_count','D','''
import numpy as np

def count_words(text):
    words = np.array(text.lower().split())
    uniq, n = np.unique(words, return_counts=True)
    return dict(zip(uniq.tolist(), n.tolist()))
''','count_words(*args)')
add('word_count','G','''
from collections import Counter

def count_words(text):
    return dict(Counter(text.lower().split()))
''','count_words(*args)')

# ---- 2 total_price ------------------------------------------------------
add('total_price','P','''
def total_price(items, tax):
    subtotal = 0.0
    for price, qty in items:
        subtotal += price * qty
    return subtotal * (1 + tax)
''','total_price(*args)')
add('total_price','O','''
class Cart:
    def __init__(self, tax):
        self.tax = tax
        self.lines = []

    def add_line(self, price, qty):
        self.lines.append((price, qty))

    def subtotal(self):
        return sum(p * q for p, q in self.lines)

    def total(self):
        return self.subtotal() * (1 + self.tax)
''','(lambda c: ([c.add_line(*l) for l in args[0]], c.total())[1])(Cart(args[1]))')
add('total_price','F','''
from functools import reduce

def total_price(items, tax):
    line = lambda pq: pq[0] * pq[1]
    return reduce(lambda a, b: a + b, map(line, items), 0.0) * (1 + tax)
''','total_price(*args)')
add('total_price','D','''
import numpy as np

def total_price(prices, quantities, tax):
    return float(np.dot(prices, quantities) * (1 + tax))
''','total_price([p for p,q in args[0]], [q for p,q in args[0]], args[1])')
add('total_price','G','''
def total_price(items, tax):
    return sum(price * qty for price, qty in items) * (1 + tax)
''','total_price(*args)')

# ---- 3 adult_names ------------------------------------------------------
add('adult_names','P','''
def adult_names(people):
    result = []
    for person in people:
        if person["age"] >= 18:
            result.append(person["name"])
    return result
''','adult_names(*args)')
add('adult_names','O','''
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def is_adult(self):
        return self.age >= 18


class Roster:
    def __init__(self, people):
        self.people = [Person(p["name"], p["age"]) for p in people]

    def adult_names(self):
        return [p.name for p in self.people if p.is_adult()]
''','Roster(*args).adult_names()')
add('adult_names','F','''
def adult_names(people):
    is_adult = lambda p: p["age"] >= 18
    return list(map(lambda p: p["name"], filter(is_adult, people)))
''','adult_names(*args)')
add('adult_names','D','''
import numpy as np

def adult_names(names, ages):
    mask = np.asarray(ages) >= 18
    return np.asarray(names)[mask].tolist()
''','adult_names([p["name"] for p in args[0]], [p["age"] for p in args[0]])')
add('adult_names','G','''
def adult_names(people):
    return [p["name"] for p in people if p["age"] >= 18]
''','adult_names(*args)')

# ---- 4 moving_average ---------------------------------------------------
add('moving_average','P','''
def moving_average(xs, k):
    out = []
    for i in range(len(xs) - k + 1):
        total = 0
        for j in range(i, i + k):
            total += xs[j]
        out.append(total / k)
    return out
''','moving_average(*args)')
add('moving_average','O','''
class MovingAverage:
    def __init__(self, k):
        self.k = k
        self.window = []
        self.values = []

    def push(self, x):
        self.window.append(x)
        if len(self.window) > self.k:
            self.window.pop(0)
        if len(self.window) == self.k:
            self.values.append(sum(self.window) / self.k)

    def run(self, xs):
        for x in xs:
            self.push(x)
        return self.values
''','MovingAverage(args[1]).run(args[0])')
add('moving_average','F','''
def moving_average(xs, k):
    windows = (xs[i:i + k] for i in range(len(xs) - k + 1))
    return list(map(lambda w: sum(w) / k, windows))
''','moving_average(*args)')
add('moving_average','D','''
import numpy as np

def moving_average(xs, k):
    c = np.cumsum(np.insert(np.asarray(xs, dtype=float), 0, 0.0))
    return ((c[k:] - c[:-k]) / k).tolist()
''','moving_average(*args)')
add('moving_average','G','''
def moving_average(xs, k):
    return [sum(xs[i:i + k]) / k for i in range(len(xs) - k + 1)]
''','moving_average(*args)')

# ---- 5 balanced ---------------------------------------------------------
add('balanced','P','''
def is_balanced(s):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return len(stack) == 0
''','is_balanced(*args)')
add('balanced','O','''
class BracketChecker:
    PAIRS = {")": "(", "]": "[", "}": "{"}

    def __init__(self):
        self.stack = []

    def feed(self, ch):
        if ch in self.PAIRS.values():
            self.stack.append(ch)
        elif ch in self.PAIRS:
            if not self.stack or self.stack.pop() != self.PAIRS[ch]:
                return False
        return True

    def check(self, s):
        return all(self.feed(c) for c in s) and not self.stack
''','BracketChecker().check(*args)')
add('balanced','F','''
def is_balanced(s, stack=()):
    if not s:
        return not stack
    ch, rest = s[0], s[1:]
    if ch in "([{":
        return is_balanced(rest, stack + (ch,))
    if ch in ")]}":
        if not stack or "([{".index(stack[-1]) != ")]}".index(ch):
            return False
        return is_balanced(rest, stack[:-1])
    return is_balanced(rest, stack)
''','is_balanced(*args)')
add('balanced','D','''
import numpy as np

def is_balanced(s):
    kind = np.array([("([{".find(c) + 1) or -(")]}".find(c) + 1) for c in s])
    kind = kind[kind != 0]
    depth = np.cumsum(np.sign(kind))
    # flat check: depth never negative and the opens/closes of each kind match as a sequence
    return bool(len(kind) == 0 or (depth.min() >= 0 and depth[-1] == 0 and _match(kind)))

def _match(kind):
    stack = np.zeros(len(kind), dtype=int)
    top = 0
    for k in kind:
        if k > 0:
            stack[top] = k
            top += 1
        else:
            top -= 1
            if top < 0 or stack[top] != -k:
                return False
    return top == 0
''','is_balanced(*args)')
add('balanced','G','''
def is_balanced(s):
    s = "".join(c for c in s if c in "()[]{}")
    while "()" in s or "[]" in s or "{}" in s:
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""
''','is_balanced(*args)')

# ---- 6 flatten ----------------------------------------------------------
add('flatten','P','''
def flatten(items):
    out = []
    stack = [items]
    while stack:
        cur = stack.pop()
        if isinstance(cur, list):
            for x in reversed(cur):
                stack.append(x)
        else:
            out.append(cur)
    return out
''','flatten(*args)')
add('flatten','O','''
class Flattener:
    def __init__(self):
        self.out = []

    def visit(self, node):
        if isinstance(node, list):
            for child in node:
                self.visit(child)
        else:
            self.out.append(node)

    def flatten(self, items):
        self.visit(items)
        return self.out
''','Flattener().flatten(*args)')
add('flatten','F','''
def flatten(items):
    if not isinstance(items, list):
        return [items]
    return [y for x in items for y in flatten(x)]
''','flatten(*args)')
add('flatten','D','''
import numpy as np

def flatten(items):
    arr = np.array(items, dtype=object)
    while any(isinstance(x, list) for x in arr):
        arr = np.concatenate([np.array(x if isinstance(x, list) else [x], dtype=object) for x in arr])
    return arr.tolist()
''','flatten(*args)')
add('flatten','G','''
def flatten(items):
    return list(walk(items))


def walk(node):
    yield from (leaf for child in node for leaf in (walk(child) if isinstance(child, list) else [child]))
''','flatten(*args)')

# ---- 7 group_by ---------------------------------------------------------
add('group_by','P','''
def group_by(records, key):
    groups = {}
    for rec in records:
        k = rec[key]
        if k not in groups:
            groups[k] = []
        groups[k].append(rec)
    return groups
''','group_by(*args)')
add('group_by','O','''
class Grouper:
    def __init__(self, key):
        self.key = key
        self.groups = {}

    def add(self, rec):
        self.groups.setdefault(rec[self.key], []).append(rec)

    def add_all(self, records):
        for rec in records:
            self.add(rec)
        return self.groups
''','Grouper(args[1]).add_all(args[0])')
add('group_by','F','''
from functools import reduce

def group_by(records, key):
    def step(acc, rec):
        k = rec[key]
        return {**acc, k: acc.get(k, []) + [rec]}
    return reduce(step, records, {})
''','group_by(*args)')
add('group_by','D','''
import numpy as np

def group_by(records, key):
    keys = np.array([r[key] for r in records])
    order = np.argsort(keys, kind="stable")
    uniq, start = np.unique(keys[order], return_index=True)
    bounds = list(start) + [len(order)]
    return {u.item(): [records[i] for i in order[bounds[j]:bounds[j + 1]]] for j, u in enumerate(uniq)}
''','group_by(*args)')
add('group_by','G','''
def group_by(records, key):
    return {k: [r for r in records if r[key] == k] for k in {r[key] for r in records}}
''','group_by(*args)')

# ---- 8 normalize --------------------------------------------------------
add('normalize','P','''
def normalize(xs):
    lo = min(xs)
    hi = max(xs)
    out = []
    for x in xs:
        out.append((x - lo) / (hi - lo))
    return out
''','normalize(*args)')
add('normalize','O','''
class MinMaxScaler:
    def __init__(self):
        self.lo = None
        self.hi = None

    def fit(self, xs):
        self.lo, self.hi = min(xs), max(xs)
        return self

    def transform(self, xs):
        return [(x - self.lo) / (self.hi - self.lo) for x in xs]
''','MinMaxScaler().fit(args[0]).transform(args[0])')
add('normalize','F','''
def normalize(xs):
    lo, hi = min(xs), max(xs)
    scale = lambda x: (x - lo) / (hi - lo)
    return list(map(scale, xs))
''','normalize(*args)')
add('normalize','D','''
import numpy as np

def normalize(xs):
    a = np.asarray(xs, dtype=float)
    return ((a - a.min()) / np.ptp(a)).tolist()
''','normalize(*args)')
add('normalize','G','''
def normalize(xs):
    return [(x - min(xs)) / (max(xs) - min(xs)) for x in xs]
''','normalize(*args)')

# ---- 9 fib --------------------------------------------------------------
add('fib','P','''
def fibonacci(n):
    seq = []
    a, b = 0, 1
    for _ in range(n):
        seq.append(a)
        a, b = b, a + b
    return seq
''','fibonacci(*args)')
add('fib','O','''
class FibonacciSequence:
    def __init__(self):
        self.a = 0
        self.b = 1

    def next(self):
        value = self.a
        self.a, self.b = self.b, self.a + self.b
        return value

    def take(self, n):
        return [self.next() for _ in range(n)]
''','FibonacciSequence().take(*args)')
add('fib','F','''
from functools import reduce

def fibonacci(n):
    step = lambda acc, _: acc + [acc[-1] + acc[-2]]
    return reduce(step, range(n - 2), [0, 1])[:n] if n > 1 else [0][:n]
''','fibonacci(*args)')
add('fib','D','''
import numpy as np

def fibonacci(n):
    seq = np.zeros(n, dtype=np.int64)
    if n > 1:
        seq[1] = 1
    for i in range(2, n):
        seq[i] = seq[i - 1] + seq[i - 2]
    return seq.tolist()
''','fibonacci(*args)')
add('fib','G','''
from itertools import islice

def fibonacci(n):
    def gen():
        a, b = 0, 1
        while True:
            yield a
            a, b = b, a + b
    return list(islice(gen(), n))
''','fibonacci(*args)')

# ---- 10 dedupe ----------------------------------------------------------
add('dedupe','P','''
def dedupe(xs):
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''','dedupe(*args)')
add('dedupe','O','''
class Deduper:
    def __init__(self):
        self.seen = set()

    def is_new(self, x):
        if x in self.seen:
            return False
        self.seen.add(x)
        return True

    def run(self, xs):
        return [x for x in xs if self.is_new(x)]
''','Deduper().run(*args)')
add('dedupe','F','''
from functools import reduce

def dedupe(xs):
    return reduce(lambda acc, x: acc if x in acc else acc + [x], xs, [])
''','dedupe(*args)')
add('dedupe','D','''
import numpy as np

def dedupe(xs):
    arr = np.asarray(xs)
    _, first = np.unique(arr, return_index=True)
    return arr[np.sort(first)].tolist()
''','dedupe(*args)')
add('dedupe','G','''
def dedupe(xs):
    return list(dict.fromkeys(xs))
''','dedupe(*args)')

# ---- 11 top_k -----------------------------------------------------------
add('top_k','P','''
def top_k(scores, k):
    names = list(scores.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if scores[names[j]] > scores[names[i]]:
                names[i], names[j] = names[j], names[i]
    return names[:k]
''','top_k(*args)')
add('top_k','O','''
class Leaderboard:
    def __init__(self):
        self.entries = []

    def record(self, name, score):
        self.entries.append((score, name))

    def top(self, k):
        return [name for score, name in sorted(self.entries, key=lambda e: -e[0])[:k]]
''','(lambda b: ([b.record(n, s) for n, s in args[0].items()], b.top(args[1]))[1])(Leaderboard())')
add('top_k','F','''
def top_k(scores, k):
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return list(map(lambda kv: kv[0], ranked[:k]))
''','top_k(*args)')
add('top_k','D','''
import numpy as np

def top_k(names, values, k):
    idx = np.argsort(-np.asarray(values), kind="stable")[:k]
    return np.asarray(names)[idx].tolist()
''','top_k(list(args[0]), list(args[0].values()), args[1])')
add('top_k','G','''
def top_k(scores, k):
    return sorted(scores, key=scores.get, reverse=True)[:k]
''','top_k(*args)')

# ---- 12 apply_transactions ---------------------------------------------
add('balance','P','''
def final_balance(start, transactions):
    balance = start
    for kind, amount in transactions:
        if kind == "deposit":
            balance += amount
        elif kind == "withdraw":
            if amount > balance:
                raise ValueError("insufficient funds")
            balance -= amount
    return balance
''','final_balance(*args)')
add('balance','O','''
class Account:
    def __init__(self, balance):
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount

    def apply(self, transactions):
        for kind, amount in transactions:
            getattr(self, kind)(amount)
        return self.balance
''','Account(args[0]).apply([("deposit" if k=="deposit" else "withdraw", a) for k, a in args[1]])')
add('balance','F','''
from functools import reduce

def final_balance(start, transactions):
    def apply(balance, tx):
        kind, amount = tx
        if kind == "withdraw" and amount > balance:
            raise ValueError("insufficient funds")
        return balance + amount if kind == "deposit" else balance - amount
    return reduce(apply, transactions, start)
''','final_balance(*args)')
add('balance','D','''
import numpy as np

def final_balance(start, kinds, amounts):
    signed = np.where(np.asarray(kinds) == "deposit", amounts, -np.asarray(amounts))
    running = start + np.cumsum(signed)
    if (running < 0).any():
        raise ValueError("insufficient funds")
    return running[-1].item() if len(running) else start
''','final_balance(args[0], [k for k,a in args[1]], [a for k,a in args[1]])')
add('balance','G','''
from itertools import accumulate

def final_balance(start, transactions):
    deltas = [a if k == "deposit" else -a for k, a in transactions]
    running = list(accumulate(deltas, initial=start))
    if min(running) < 0:
        raise ValueError("insufficient funds")
    return running[-1]
''','final_balance(*args)')

STYLES = ['P','O','F','D','G']
STYLE_NAMES = {'P':'procedural','O':'object-oriented','F':'functional','D':'data-oriented','G':'declarative/idiomatic one-liner'}
