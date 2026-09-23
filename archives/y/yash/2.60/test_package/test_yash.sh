#!/bin/sh
# Functional test for the yash shell package.
# $1 = package bin dir.
set -e

BINDIR="$1"
YASH="${BINDIR:+$BINDIR/}yash"

# 1. version probe
"$YASH" --version > version.out 2>&1
grep -q "2.60" version.out || { echo "FAIL: --version"; exit 1; }

# 2. basic script execution: echo + command substitution + arithmetic
out=$("$YASH" -c 'echo "hello $(echo yash) $((6 * 7))"')
[ "$out" = "hello yash 42" ] || { echo "FAIL: basic script: $out"; exit 1; }

# 3. POSIX features: for loop + case + parameter expansion
out=$("$YASH" -c 'x=""; for i in a b c; do x="$x$i"; done; case $x in abc) echo ok;; *) echo bad;; esac')
[ "$out" = "ok" ] || { echo "FAIL: posix features: $out"; exit 1; }

# 4. yash extension: array assignment + 1-based indexing
out=$("$YASH" -c 'arr=(foo bar); echo "${arr[1]}/${arr[2]}"' 2>/dev/null)
[ "$out" = "foo/bar" ] || { echo "FAIL: array extension: $out"; exit 1; }

# 5. pipeline + exit status propagation
out=$("$YASH" -c 'printf "x\ny\n" | while read -r l; do echo "got:$l"; done')
[ "$out" = "got:x
got:y" ] || { echo "FAIL: pipeline: $out"; exit 1; }

# 6. exit status propagation
rc=0
"$YASH" -c 'exit 3' || rc=$?
[ "$rc" -eq 3 ] || { echo "FAIL: exit status propagation rc=$rc"; exit 1; }

echo "yash CLI test: PASS"
