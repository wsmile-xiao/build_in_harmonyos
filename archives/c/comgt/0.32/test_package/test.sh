#!/usr/bin/env bash
# test_package/test.sh — behavior test for the installed comgt executable.
# comgt -V/-h print the version banner. NOTE: upstream exits with code 1 by
# design after printing (ext(1) in comgt.c) — the assertions check the real
# stdout content and accept the documented exit code 1.
set -euo pipefail

fail() { echo "FAIL: $1"; exit 1; }

echo "[test] comgt -V version banner"
out=$(comgt -V 2>/dev/null) || rc=$?
rc=${rc:-0}
case "$out" in
  *"comgt version 0.32"*) : ;;
  *) fail "comgt -V -> unexpected banner '$out'" ;;
esac
[ "$rc" -le 1 ] || fail "comgt -V -> unexpected exit code $rc"
echo "PASS: comgt -V prints version banner (exit code $rc, upstream ext(1) by design)"
rc=0

echo "[test] comgt -h usage pointer"
out=$(comgt -h 2>/dev/null) || rc=$?
rc=${rc:-0}
case "$out" in
  *"comgt help"*) : ;;
  *) fail "comgt -h -> missing usage pointer '$out'" ;;
esac
[ "$rc" -le 1 ] || fail "comgt -h -> unexpected exit code $rc"
echo "PASS: comgt -h prints usage pointer (exit code $rc, upstream ext(1) by design)"
rc=0

echo "ALL PASS: comgt behavior test (2 assertions)"
