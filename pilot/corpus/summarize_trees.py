"""Per repo: number of source files by language from `git ls-tree -r --name-only HEAD` of a blobless depth=1 clone
(trees only, no file contents downloaded), excluding vendored / generated / test paths.
usage: python3 -I summarize_trees.py <probe dir> <out tsv>

File counts only. `ls-tree -l` (sizes) makes git download every blob of a blobless clone, which turned out to cost as much as
a full clone, so sizes come later from the real checkout."""
import sys, os, re, collections

EXT = {'py': 'Python', 'ts': 'TypeScript', 'tsx': 'TypeScript', 'js': 'JavaScript', 'mjs': 'JavaScript', 'jsx': 'JavaScript', 'vue': 'Vue', 'java': 'Java', 'kt': 'Kotlin',
       'cs': 'C#', 'c': 'C', 'cc': 'C++', 'cpp': 'C++', 'cxx': 'C++', 'hpp': 'C++', 'go': 'Go', 'rs': 'Rust', 'php': 'PHP', 'rb': 'Ruby', 'swift': 'Swift',
       'pl': 'Perl', 'pm': 'Perl', 'scala': 'Scala', 'ex': 'Elixir', 'exs': 'Elixir', 'hs': 'Haskell', 'm': 'Objective-C', 'mm': 'Objective-C++'}
SKIP = re.compile(r'(^|/)(node_modules|vendor|third_party|thirdparty|3rdparty|external|deps|testdata|fixtures?|tests?|test|spec|__tests__|examples?|docs?|benchmarks?|generated|gen|dist|build)(/|$)|\.(min|pb|generated)\.|_test\.go$|\.d\.ts$|_generated|\.stories\.')
probe, out = sys.argv[1], sys.argv[2]
with open(out, 'w') as o:
    o.write('repo\tfiles_in_tree\tsource_files(non-test)\ttop_languages(files)\n')
    for f in sorted(os.listdir(probe)):
        if not f.endswith('.names'): continue
        by = collections.Counter(); alln = 0
        for line in open(os.path.join(probe, f), errors='replace'):
            p = line.rstrip('\n'); alln += 1
            ext = p.rsplit('.', 1)[-1].lower() if '.' in p.rsplit('/', 1)[-1] else ''
            lang = EXT.get(ext)
            if lang and not SKIP.search(p.lower()): by[lang] += 1
        o.write(f"{f[:-6]}\t{alln}\t{sum(by.values())}\t" + ', '.join(f'{l} {n}' for l, n in by.most_common(4)) + '\n')
print(open(out).read())
