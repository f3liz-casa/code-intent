#!/bin/bash
d=/tmp/mk/probe/$(echo $2 | tr / _)
[ -d $d/.git ] || timeout 600 git clone -q --depth=1 --filter=blob:none --no-checkout https://github.com/$2 $d 2>/dev/null || { echo "$1 $2 FAIL"; exit 0; }
git -C $d ls-tree -r --name-only HEAD > $d.names 2>/dev/null
echo "$1 $2 $(git -C $d rev-parse --short HEAD) $(git -C $d log -1 --format=%cs) $(wc -l < $d.names)"
