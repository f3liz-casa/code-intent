"""Independent hand check: well-known stdlib functions with the tag I expect (written before looking at the preset output)."""
import sys; sys.path.insert(0, '.')
from build_preset import Preset
P = Preset()
TRUTH = {  # qualified name -> expected tag set (empty = pure computation)
 'shutil.copyfile': {'fs'}, 'shutil.rmtree': {'fs'}, 'shutil.move': {'fs'}, 'glob.glob': {'fs'}, 'os.listdir': {'fs'}, 'os.path.exists': {'fs'}, 'os.path.join': set(),
 'os.makedirs': {'fs'}, 'os.getcwd': {'fs'}, 'tempfile.mkdtemp': {'fs'}, 'filecmp.cmp': {'fs'}, 'pathlib.Path.read_text': {'fs'}, 'fileinput.input': {'fs'},
 'urllib.request.urlopen': {'net'}, 'urllib.request.urlretrieve': {'net', 'fs'}, 'http.client.HTTPConnection.request': {'net'}, 'socket.create_connection': {'net'},
 'ftplib.FTP.connect': {'net'}, 'smtplib.SMTP.sendmail': {'net'}, 'smtplib.SMTP.connect': {'net'}, 'ssl.create_default_context': {'net'}, 'urllib.parse.urlparse': set(), 'urllib.parse.quote': set(),
 'subprocess.run': {'proc'}, 'subprocess.check_output': {'proc'}, 'os.system': {'proc'}, 'os.getpid': set(),
 'time.sleep': {'clock'}, 'time.time': {'clock'}, 'datetime.datetime.now': {'clock'}, 'os.getenv': {'env'}, 'os.urandom': {'random'},
 'json.dumps': set(), 'json.loads': set(), 're.sub': set(), 're.compile': set(), 'textwrap.dedent': set(), 'math.sqrt': set(), 'statistics.mean': set(), 'collections.Counter': set(),
 'itertools.chain': set(), 'functools.reduce': set(), 'heapq.nlargest': set(), 'bisect.bisect_left': set(), 'copy.deepcopy': set(), 'string.capwords': set(),
 'threading.Thread.start': {'thread'}, 'logging.info': {'console', 'fs', 'thread', 'clock'}, 'pprint.pprint': {'console'}, 'getpass.getpass': {'console', 'fs'}, 'csv.reader': set(),
 'sqlite3.connect': set(), 'zipfile.ZipFile.extractall': {'fs'}, 'tarfile.open': {'fs'},
}
ok_tag = ok_pure = wrong = missing = n_tag = n_pure = 0; rows = []
for q, exp in TRUTH.items():
    r = P.resolve_full(q)
    got = set(P.tags.get(r[1], set())) if r and r[0] == 'func' else ({r[1]} if r and r[0] == 'tag' else set())
    ioexp, ioget = exp & {'fs', 'net', 'proc'}, got & {'fs', 'net', 'proc'}
    if exp: 
        n_tag += 1
        hit = bool(exp & got); ok_tag += hit
    else:
        n_pure += 1; hit = not ioget; ok_pure += hit
    rows.append((q, sorted(exp), sorted(got), 'ok' if hit else 'MISS'))
for r in rows: print('%-40s exp=%-22s got=%-26s %s' % (r[0], r[1], r[2], r[3]))
print('tagged-expected: found at least one expected tag %d/%d | pure-expected: no IO tag %d/%d' % (ok_tag, n_tag, ok_pure, n_pure))
