#!/bin/sh
# CLI test for the libexplain `explain` command (static binary).
# Usage: explain -e <errno> <function> [args] — it explains an errno for
# a function call verbosely (it does NOT execute commands).
# $1 = package bin dir.
set -e

BINDIR="$1"
EXPLAIN="${BINDIR:+$BINDIR/}explain"

work="${TMPDIR:-.}/libexplain_cli_test.$$"
mkdir -p "$work"
cd "$work"
trap 'cd /; rmdir "$work" 2>/dev/null || true' EXIT

# 1. version probe
out0=$("$EXPLAIN" -V 2>&1)
echo "$out0" | tr '\n' ' ' | grep -q "libexplain version 1.4" || { echo "FAIL: -V"; exit 1; }

# 2. verbose ENOENT explanation for open(2)
out=$("$EXPLAIN" -e ENOENT open /nonexistent/xyz 0 2>&1)
echo "$out" | head -3
# CLI wraps at terminal width — flatten before matching phrases
flat=$(printf '%s\n' "$out" | tr '\n' ' ' | tr -s ' ')
echo "$flat" | grep -qi "No such file or directory" || {
    echo "FAIL: no ENOENT explanation"; exit 1; }
# libexplain adds the syscall name and errno number — richer than strerror
echo "$flat" | grep -qi "open" || { echo "FAIL: no syscall name"; exit 1; }

echo "libexplain CLI test: PASS"
