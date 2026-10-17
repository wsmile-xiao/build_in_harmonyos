#!/bin/sh
# chiark-utils test_package smoke test — real execution of packaged binaries.
# Usage: sh test_smoke.sh <package_bindir>
# Asserts: (1) with-lock-ex really acquires a file lock and runs a child
# under it; (2) summer really hashes a file given by name on stdin.
set -eu

BINDIR="${1:?usage: test_smoke.sh <package-bindir>}"
WORK="$(cd "$(dirname "$0")" && pwd)"
cd "$WORK"

# cleanup any previous run artifacts
rm -f test.lock lockproof.txt sumfile.txt summer.out

# 1) real lock acquisition + child execution under the lock
seq 1 3 > lockproof.txt
rm -f test.lock
"$BINDIR/with-lock-ex" -w test.lock sh -c 'cat lockproof.txt' > lockout.txt
grep -q '^2$' lockout.txt
echo "PASS: with-lock-ex lock + child execution"

# 2) real checksum: summer reads FILENAMES from stdin ("startpoints")
seq 1 20 > sumfile.txt
ls sumfile.txt | "$BINDIR/summer" > summer.out
grep -q sumfile summer.out
grep -qE '[0-9a-f]{32}|[0-9a-f]{64}' summer.out
echo "PASS: summer checksum output"

rm -f test.lock lockproof.txt sumfile.txt summer.out lockout.txt
echo "ALL SMOKE TESTS PASSED"
