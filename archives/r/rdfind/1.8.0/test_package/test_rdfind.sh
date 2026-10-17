#!/usr/bin/env bash
# Functional test for the packaged rdfind CLI.
#
# Builds a small tree containing one duplicate pair and one unique file, runs
# the packaged binary over it, and verifies the results file that rdfind
# generates: the two identical files must be classified as a duplicate pair
# (DUPTYPE_FIRST_OCCURRENCE + DUPTYPE_WITHIN_SAME_TREE) while the unique file
# must not appear at all.
set -euo pipefail

RDFIND_BIN="${RDFIND_BIN:-rdfind}"

# R10/E002: on the OHOS device /tmp is a read-only erofs mount, so temporary
# files must go to $TMPDIR (which the worker sets) or a writable fallback.
_tmp="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_tmp"
treedir="$(mktemp -d "$_tmp/rdfind-tree.XXXXXX")"
outdir="$(mktemp -d "$_tmp/rdfind-out.XXXXXX")"
cleanup() { rm -rf "$treedir" "$outdir"; }
trap cleanup EXIT

mkdir -p "$treedir/one" "$treedir/two"
printf 'rdfind duplicate payload\n' > "$treedir/one/a.txt"
cp "$treedir/one/a.txt" "$treedir/two/b.txt"
printf 'unique payload\n' > "$treedir/one/unique.txt"

"$RDFIND_BIN" -checksum sha1 -outputname "$outdir/results.txt" "$treedir" > "$outdir/rdfind.log" 2>&1

results="$outdir/results.txt"
if [ ! -f "$results" ]; then
  echo "rdfind did not produce a results file"
  cat "$outdir/rdfind.log"
  exit 1
fi

for expected in 'DUPTYPE_FIRST_OCCURRENCE' 'DUPTYPE_WITHIN_SAME_TREE' 'a.txt' 'b.txt'; do
  if ! grep -q "$expected" "$results"; then
    echo "results file is missing '$expected'"
    cat "$results"
    exit 1
  fi
done

if grep -q 'unique.txt' "$results"; then
  echo "the unique file was wrongly reported as a duplicate"
  cat "$results"
  exit 1
fi

echo "rdfind smoke test passed"
