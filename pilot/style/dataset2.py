"""IO (filesystem, network) and glue intents, same five styles. Imported after dataset.py."""
from dataset import add, S, STYLES

# ---- fs: read_lines -----------------------------------------------------
add('read_lines','P','''
def read_lines(path):
    result = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                result.append(line)
    return result
''','read_lines(*args)')
add('read_lines','O','''
class LineReader:
    def __init__(self, path):
        self.path = path
        self.lines = []

    def load(self):
        with open(self.path) as f:
            self.lines = [ln.strip() for ln in f if ln.strip()]
        return self

    def get(self):
        return self.lines
''','LineReader(*args).load().get()')
add('read_lines','F','''
def read_lines(path):
    with open(path) as f:
        return list(filter(None, map(str.strip, f.read().splitlines())))
''','read_lines(*args)')
add('read_lines','D','''
import numpy as np

def read_lines(path):
    with open(path) as f:
        lines = np.char.strip(np.array(f.read().splitlines(), dtype=str))
    return lines[np.char.str_len(lines) > 0].tolist()
''','read_lines(*args)')
add('read_lines','G','''
from pathlib import Path

def read_lines(path):
    return [ln.strip() for ln in Path(path).read_text().splitlines() if ln.strip()]
''','read_lines(*args)')

# ---- fs: list_by_ext ----------------------------------------------------
add('list_by_ext','P','''
import os

def files_with_ext(directory, ext):
    found = []
    for name in os.listdir(directory):
        if name.endswith(ext):
            found.append(name)
    found.sort()
    return found
''','files_with_ext(*args)')
add('list_by_ext','O','''
import os

class DirectoryScanner:
    def __init__(self, directory):
        self.directory = directory

    def names(self):
        return os.listdir(self.directory)

    def with_ext(self, ext):
        return sorted(n for n in self.names() if n.endswith(ext))
''','DirectoryScanner(args[0]).with_ext(args[1])')
add('list_by_ext','F','''
import os

def files_with_ext(directory, ext):
    return sorted(filter(lambda n: n.endswith(ext), os.listdir(directory)))
''','files_with_ext(*args)')
add('list_by_ext','D','''
import os
import numpy as np

def files_with_ext(directory, ext):
    names = np.array(os.listdir(directory), dtype=str)
    return np.sort(names[np.char.endswith(names, ext)]).tolist()
''','files_with_ext(*args)')
add('list_by_ext','G','''
from pathlib import Path

def files_with_ext(directory, ext):
    return sorted(p.name for p in Path(directory).iterdir() if p.name.endswith(ext))
''','files_with_ext(*args)')

# ---- fs: save_json ------------------------------------------------------
add('save_json','P','''
import json

def save_json(path, obj):
    text = json.dumps(obj, indent=2)
    f = open(path, "w")
    f.write(text)
    f.close()
''','save_json(*args)')
add('save_json','O','''
import json

class JsonStore:
    def __init__(self, path):
        self.path = path

    def encode(self, obj):
        return json.dumps(obj, indent=2)

    def save(self, obj):
        with open(self.path, "w") as f:
            f.write(self.encode(obj))
''','JsonStore(args[0]).save(args[1])')
add('save_json','F','''
import json
from functools import partial

def save_json(path, obj):
    write = partial(print, file=open(path, "w"), end="")
    return write(json.dumps(obj, indent=2))
''','save_json(*args)')
add('save_json','D','''
import json
import numpy as np

def save_json(path, obj):
    payload = np.frombuffer(json.dumps(obj, indent=2).encode(), dtype=np.uint8)
    payload.tofile(path)
''','save_json(*args)')
add('save_json','G','''
import json
from pathlib import Path

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2))
''','save_json(*args)')

# ---- net: fetch_json with retry ----------------------------------------
add('fetch_json','P','''
import json
import urllib.request

def fetch_json(url):
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except OSError as e:
            last_error = e
    raise last_error
''','fetch_json(*args)')
add('fetch_json','O','''
import json
import urllib.request

class JsonClient:
    def __init__(self, retries=3, timeout=5):
        self.retries = retries
        self.timeout = timeout

    def _get_once(self, url):
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def get(self, url):
        error = None
        for _ in range(self.retries):
            try:
                return self._get_once(url)
            except OSError as e:
                error = e
        raise error
''','JsonClient().get(*args)')
add('fetch_json','F','''
import json
import urllib.request

def fetch_json(url, attempts=3):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except OSError:
        if attempts <= 1:
            raise
        return fetch_json(url, attempts - 1)
''','fetch_json(*args)')
add('fetch_json','D','''
import json
import urllib.request
import numpy as np

def fetch_json(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                raw = np.frombuffer(resp.read(), dtype=np.uint8)
            return json.loads(raw.tobytes().decode())
        except OSError:
            continue
    raise OSError("unreachable")
''','fetch_json(*args)')
add('fetch_json','G','''
import json
import urllib.request
from itertools import islice

def fetch_json(url):
    def attempts():
        while True:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    yield json.load(resp)
            except OSError:
                yield None
    return next(r for r in islice(attempts(), 3) if r is not None)
''','fetch_json(*args)')

# ---- net: download to file ---------------------------------------------
add('download','P','''
import urllib.request

def download(url, path):
    resp = urllib.request.urlopen(url, timeout=5)
    data = resp.read()
    resp.close()
    f = open(path, "wb")
    f.write(data)
    f.close()
    return len(data)
''','download(*args)')
add('download','O','''
import urllib.request

class Downloader:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.bytes_written = 0

    def fetch(self, url):
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return resp.read()

    def save(self, url, path):
        data = self.fetch(url)
        with open(path, "wb") as f:
            f.write(data)
        self.bytes_written += len(data)
        return len(data)
''','Downloader().save(*args)')
add('download','F','''
import urllib.request

def download(url, path):
    fetch = lambda u: urllib.request.urlopen(u, timeout=5).read()
    write = lambda data: (open(path, "wb").write(data), len(data))[1]
    return write(fetch(url))
''','download(*args)')
add('download','D','''
import urllib.request
import numpy as np

def download(url, path):
    with urllib.request.urlopen(url, timeout=5) as resp:
        buf = np.frombuffer(resp.read(), dtype=np.uint8)
    buf.tofile(path)
    return buf.size
''','download(*args)')
add('download','G','''
import urllib.request
from pathlib import Path

def download(url, path):
    return Path(path).write_bytes(urllib.request.urlopen(url, timeout=5).read())
''','download(*args)')

# ---- glue: adults from file --------------------------------------------
add('glue_adults','P','''
def adults_from_file(path):
    records = read_json(path)
    names = adult_names(records)
    return names
''','adults_from_file(*args)')
add('glue_adults','O','''
class AdultsService:
    def __init__(self, loader, selector):
        self.loader = loader
        self.selector = selector

    def run(self, path):
        return self.selector(self.loader(path))
''','AdultsService(read_json, adult_names).run(*args)')
add('glue_adults','F','''
from functools import reduce

def adults_from_file(path):
    return reduce(lambda acc, step: step(acc), [read_json, adult_names], path)
''','adults_from_file(*args)')
add('glue_adults','D','''
def adults_from_file(path):
    records = read_json(path)
    names, ages = [r["name"] for r in records], [r["age"] for r in records]
    return adult_names_columns(names, ages)
''','adults_from_file(*args)')
add('glue_adults','G','''
def adults_from_file(path):
    return adult_names(read_json(path))
''','adults_from_file(*args)')

# ---- glue: report -------------------------------------------------------
add('glue_report','P','''
def report(items, tax):
    total = total_price(items, tax)
    line = "Total: " + format(total, ".2f")
    return line
''','report(*args)')
add('glue_report','O','''
class ReportBuilder:
    def __init__(self, pricer, formatter):
        self.pricer = pricer
        self.formatter = formatter

    def build(self, items, tax):
        return self.formatter(self.pricer(items, tax))
''','ReportBuilder(total_price, lambda t: "Total: %.2f" % t).build(*args)')
add('glue_report','F','''
def report(items, tax):
    return (lambda total: f"Total: {total:.2f}")(total_price(items, tax))
''','report(*args)')
add('glue_report','D','''
def report(items, tax):
    prices, quantities = zip(*items)
    return f"Total: {total_price_columns(prices, quantities, tax):.2f}"
''','report(*args)')
add('glue_report','G','''
def report(items, tax):
    return f"Total: {total_price(items, tax):.2f}"
''','report(*args)')

# ---- glue: dispatch -----------------------------------------------------
add('glue_dispatch','P','''
def dispatch(command, values):
    if command == "sum":
        return sum(values)
    elif command == "max":
        return max(values)
    elif command == "count":
        return len(values)
    else:
        raise KeyError(command)
''','dispatch(*args)')
add('glue_dispatch','O','''
class CommandRouter:
    def __init__(self):
        self.handlers = {}

    def register(self, name, fn):
        self.handlers[name] = fn

    def dispatch(self, command, values):
        return self.handlers[command](values)
''','(lambda r: ([r.register(k, f) for k, f in {"sum": sum, "max": max, "count": len}.items()], r.dispatch(*args))[1])(CommandRouter())')
add('glue_dispatch','F','''
HANDLERS = {"sum": sum, "max": max, "count": len}

def dispatch(command, values):
    return HANDLERS[command](values)
''','dispatch(*args)')
add('glue_dispatch','D','''
import numpy as np

TABLE = {"sum": np.sum, "max": np.max, "count": np.size}

def dispatch(command, values):
    return np.asarray(TABLE[command](np.asarray(values))).item()
''','dispatch(*args)')
add('glue_dispatch','G','''
def dispatch(command, values):
    return {"sum": sum, "max": max, "count": len}[command](values)
''','dispatch(*args)')

CATEGORY = {   # intent -> (top, sub)
 'word_count': ('compute', 'collections'), 'group_by': ('compute', 'collections'), 'flatten': ('compute', 'collections'),
 'dedupe': ('compute', 'collections'), 'top_k': ('compute', 'collections'), 'adult_names': ('compute', 'collections'),
 'total_price': ('compute', 'numeric'), 'moving_average': ('compute', 'numeric'), 'normalize': ('compute', 'numeric'), 'fib': ('compute', 'numeric'),
 'balanced': ('compute', 'logic'), 'balance': ('compute', 'logic'),
 'read_lines': ('io', 'filesystem'), 'list_by_ext': ('io', 'filesystem'), 'save_json': ('io', 'filesystem'),
 'fetch_json': ('io', 'network'), 'download': ('io', 'network'),
 'glue_adults': ('glue', 'compose'), 'glue_report': ('glue', 'compose'), 'glue_dispatch': ('glue', 'compose'),
}
