#!/usr/bin/env bash
# Upstream test set for xmlindent 0.2.18 — run from the unpacked source root.
#
# WHAT UPSTREAM SHIPS
# -------------------
# xmlindent 0.2.18 has NO `check`/`test` Makefile target and no test runner
# script.  What it does ship is exactly one regression fixture pair, added in
# commit "#3 parse: Fix whitespace consumption within text nodes" (2020-02-23,
# see ChangeLog):
#
#     tests/whitespace-in-content.orig.xml       (input)
#     tests/whitespace-in-content.expected.xml   (expected output)
#
# That fixture is the regression test for the whitespace-in-content fix and is
# runnable as-is: the tool is a stdin/stdout filter, so the test is
# `xmlindent orig` compared byte-for-byte against `expected`.
#
# This script executes that fixture.  It is the COMPLETE upstream test set for
# this version — no case is skipped, filtered or excluded.  upstream_total = 1.
#
# The script is intentionally hermetic: it does not touch the network and uses
# ${TMPDIR} (on OpenHarmony /tmp is a read-only erofs mount).
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
cd "$here"

BIN="${XMLINDENT_BIN:-./xmlindent}"
if [ ! -x "$BIN" ]; then
    echo "xmlindent binary not found/executable: $BIN" >&2
    exit 1
fi

tmp="${TMPDIR:-.}/xmlindent-upstream.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

fail=0
total=0

# --- upstream case 1/1: tests/whitespace-in-content ------------------------
total=$((total + 1))
orig="tests/whitespace-in-content.orig.xml"
expected="tests/whitespace-in-content.expected.xml"

if [ ! -f "$orig" ] || [ ! -f "$expected" ]; then
    echo "FAIL  whitespace-in-content: fixture files missing" >&2
    fail=$((fail + 1))
elif ! "$BIN" "$orig" > "$tmp/got.xml" 2> "$tmp/got.err"; then
    echo "FAIL  whitespace-in-content: xmlindent exited non-zero" >&2
    cat "$tmp/got.err" >&2
    fail=$((fail + 1))
elif ! cmp -s "$tmp/got.xml" "$expected"; then
    echo "FAIL  whitespace-in-content: output differs from expected" >&2
    diff -u "$expected" "$tmp/got.xml" >&2 || true
    fail=$((fail + 1))
else
    echo "ok    whitespace-in-content (1/1)"
fi

echo "upstream tests: $((total - fail))/$total passed"
[ "$fail" -eq 0 ] || exit 1
