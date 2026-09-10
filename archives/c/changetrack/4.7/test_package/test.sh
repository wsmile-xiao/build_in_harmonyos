#!/usr/bin/env bash
# test_package/test.sh — consumer smoke test for changetrack
# Runs in an env where bin/ is on PATH, rcs/5.10.1 bindir is on PATH
# (conanrun env), and GNU diffutils precedes toybox. Mirrors the assertions
# of test_package/conanfile.py.
set -eu

echo "[test] changetrack -v"
vout="$(changetrack -v)"
echo "$vout" | grep -q "4.7"
echo "[ok] changetrack -v OK (version 4.7)"

echo "[test] changetrack -h"
# -h exits 1 by upstream design; assert on output content
hout="$(changetrack -h 2>&1 || true)"
echo "$hout" | grep -q "This is changetrack, version"
echo "[ok] changetrack -h OK (usage text)"

echo "[test] changetrack functional loopback (-r: no RCS)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
target="$work/target.txt"
printf 'line1\nline2\nline3\n' > "$target"
printf '%s\n' "$target" > "$work/ct.conf"

changetrack -r -q -c "$work/ct.conf" -d "$work/history" -e
# changetrack maps the monitored absolute path into artifact names ('/' -> ':')
base="$(printf '%s' "$target" | tr '/' ':')"
base="${base#:}"
test -f "$work/history/$base.yesterday"
grep -q "New file" "$work/history/$base.history"
echo "[ok] first run: New file recorded, snapshot written"

printf 'line1\nCHANGED\nline3\n' > "$target"
changetrack -r -q -c "$work/ct.conf" -d "$work/history" -e
grep -q "Changes made on" "$work/history/$base.history"
grep -q "CHANGED" "$work/history/$base.history"
grep -q "2c" "$work/history/$base.ed"
grep -q "CHANGED" "$work/history/$base.ed"
grep -q "CHANGED" "$work/history/$base.yesterday"
echo "[ok] second run: change detected, history + diff -e ed script written"

echo "[test] rcs -V (upstream make test final check)"
rcs -V > /dev/null
echo "[ok] rcs -V OK"

echo "[test] changetrack full mode (RCS revision storage)"
target2="$work/tracked.txt"
printf 'alpha\nbeta\n' > "$target2"
printf '%s\n' "$target2" > "$work/ct-rcs.conf"
base2="$(printf '%s' "$target2" | tr '/' ':')"
base2="${base2#:}"

changetrack -q -c "$work/ct-rcs.conf" -d "$work/history-rcs" -e
test -f "$work/history-rcs/RCS/$base2,v"
printf 'alpha\nGAMMA\n' > "$target2"
changetrack -q -c "$work/ct-rcs.conf" -d "$work/history-rcs" -e
revisions="$(rlog "$work/history-rcs/RCS/$base2,v" | grep -c "^revision")"
test "$revisions" -ge 2
grep -q "Changes made on" "$work/history-rcs/$base2.history"
echo "[ok] full mode: ,v file with $revisions revisions + history log"

echo "[test] upstream make test equivalence (which perl + 5 perl modules + rcs -V)"
which perl > /dev/null
perl -e 'use File::Copy; use Getopt::Std; use File::Path; use FileHandle; use strict;'
rcs -V > /dev/null
echo "[ok] upstream make test checks all pass"

echo "[test] changetrack smoke test: PASS"
