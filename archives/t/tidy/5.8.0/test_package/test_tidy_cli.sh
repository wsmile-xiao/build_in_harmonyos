#!/bin/sh
# Consumer test for the tidy CLI (statically linked binary).
# $1 = package bin dir.
set -e

BINDIR="$1"
TIDY="${BINDIR:+$BINDIR/}tidy"

work="${TMPDIR:-.}/tidy_cli_test.$$"
mkdir -p "$work"
cd "$work"

fail() { echo "FAIL: $1"; exit 1; }

# 1. version probe
out=$("$TIDY" -version 2>&1) || fail "-version exited nonzero"
echo "$out" | grep -q "HTML Tidy" || fail "version output missing 'HTML Tidy'"

# 2. clean document passes with exit 0
printf '<!DOCTYPE html>\n<html><head><title>t</title></head><body><p>ok</p></body></html>\n' > good.html
"$TIDY" -q -errors good.html || fail "clean document reported errors"

# 3. broken document is diagnosed (nonzero exit + diagnostics)
printf '<html><head></head><body><p>unclosed\n' > bad.html
rc=0
"$TIDY" -q -errors bad.html > out.txt 2>&1 || rc=$?
[ "$rc" -ne 0 ] || fail "broken document exited 0"
[ -s out.txt ] || fail "no diagnostics for broken document"

echo "tidy CLI consumer test: PASS"
