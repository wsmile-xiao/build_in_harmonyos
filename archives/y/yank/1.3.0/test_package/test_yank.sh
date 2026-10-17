#!/bin/sh
# CLI test for yank.  $1 = package bin dir.
# yank is an interactive selector (reads keys from /dev/tty and ignores
# SIGTERM in UI mode) — only probe paths that exit before the UI:
# version probe and option-error rejection.  Every invocation is wrapped
# in timeout -s KILL as a hard backstop (TERM does not stop yank's UI).
set -e

BINDIR="$1"
YANK="${BINDIR:+$BINDIR/}yank"

# 1. version probe
out=$(timeout -s KILL 10 "$YANK" -v)
[ "$out" = "yank 1.3.0" ] || { echo "FAIL: -v: $out"; exit 1; }

# 2. unknown option → usage error, non-zero exit, before any UI
rc=0
out2=$(timeout -s KILL 10 "$YANK" -z </dev/null 2>&1) || rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: unknown option accepted"; exit 1; }
echo "$out2" | grep -qiE "usage|unknown|invalid" || { echo "FAIL: no usage message: $out2"; exit 1; }

echo "yank CLI test: PASS"
