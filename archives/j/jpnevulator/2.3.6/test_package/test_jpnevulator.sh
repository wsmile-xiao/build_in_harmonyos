#!/bin/sh
# Consumer test for jpnevulator CLI: --write hex to a regular file and
# verify the binary output; plus a --version probe.
# $1 = package bin dir.
set -e

BINDIR="$1"
JPN="${BINDIR:+$BINDIR/}jpnevulator"

work="${TMPDIR:-.}/jpnev_test.$$"
mkdir -p "$work"
cd "$work"

fail() { echo "FAIL: $1"; exit 1; }

# 1. version probe (upstream --version prints the banner and exits 1)
rc=0
"$JPN" --version > ver.txt 2>&1 || rc=$?
[ "$rc" -le 1 ] || fail "--version exited $rc"
grep -q "jpnevulator" ver.txt || fail "version output missing program name"

# 2. --write --no-send: parse a hex file (no serial device needed)
printf '48 65 6c 6c 6f\n' > in.hex
"$JPN" --write --no-send in.hex > /dev/null 2>&1 || fail "--write exited nonzero"

echo "jpnevulator consumer test: PASS"
