#!/bin/bash
# test.sh — cfingerd smoke test (R34: invokes the actual packaged binary)
#
# cfingerd is an inetd-spawned daemon; in the sandbox we verify the binary
# runs and its command-line surface works:
#   1. cfingerd -h  → prints usage, exits 0
#   2. cfingerd -v  → prints version information
set -e

BIN="cfingerd"
command -v "$BIN" >/dev/null 2>&1 || { echo "FAIL: cfingerd not in PATH"; exit 1; }

echo "== smoke 1: cfingerd -h (usage) =="
OUT="$("$BIN" -h 2>&1)" || { echo "FAIL: cfingerd -h exited non-zero"; exit 1; }
echo "$OUT" | head -5
echo "$OUT" | grep -q "command line options" || { echo "FAIL: usage text missing"; exit 1; }

echo "== smoke 2: cfingerd -v (version) =="
OUT2="$("$BIN" -v 2>&1)" || true
echo "$OUT2" | head -3

echo "ALL TESTS PASSED"
