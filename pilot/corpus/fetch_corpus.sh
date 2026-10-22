#!/bin/bash
# Shallow-clone the corpus into $1 (default ./corpus), smallest first, stopping when free disk drops below 3 GB.
# usage: fetch_corpus.sh <dest> [repos.tsv]
dest=${1:-./corpus}; list=${2:-$(dirname "$0")/repos.tsv}; mkdir -p "$dest"
tail -n +2 "$list" | cut -f2 | while read -r repo; do
	d="$dest/$(echo "$repo" | tr / _)"
	[ -d "$d/.git" ] && continue
	avail=$(df --output=avail -BG "$dest" | tail -1 | tr -dc 0-9)
	[ "$avail" -lt 3 ] && { echo "stop: ${avail}G free"; break; }
	git clone -q --depth=1 "https://github.com/$repo" "$d" && echo "ok $repo $(du -sh "$d" | cut -f1)"
done
