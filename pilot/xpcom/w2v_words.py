import re
"""Identifier-word sentences from every C++/JS function in the Firefox checkout (minus the evaluation pairs)."""
def words(code):
    ids = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', code); out = []
    for i in ids:
        for part in re.split(r'_+', i):
            out += [w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+', part)]
    return [w for w in out if len(w) > 1]
