#!/bin/sh
# CLI test for the yacas console: evaluates expressions via -c/-pc.
# $1 = package bin dir, $2 = package share dir (scripts root).
set -e

BINDIR="$1"
SHAREDIR="$2"
YACAS="${BINDIR:+$BINDIR/}yacas"
ROOT="${SHAREDIR:+$SHAREDIR/}yacas/scripts"

work="${TMPDIR:-.}/yacas_cli_test.$$"
mkdir -p "$work"
cd "$work"
trap 'cd /; rmdir "$work" 2>/dev/null || true' EXIT

# 1. version probe: the console prints "This is Yacas version 'X'" in
# its startup banner (upstream has no --version flag)
out0=$(printf 'Exit();\n' | "$YACAS" -pc --rootdir "$ROOT" 2>/dev/null)
echo "$out0" | grep -q "Yacas version '1.9.1'" || { echo "FAIL: version banner"; exit 1; }

# 2. script-library dependent evaluation (proves share/yacas/scripts shipped)
out=$(printf 'Simplify(1/3+1/6);\nExit();\n' | "$YACAS" -pc --rootdir "$ROOT" 2>/dev/null)
echo "$out"
echo "$out" | grep -q "1/2" || { echo "FAIL: Simplify via console"; exit 1; }

echo "yacas CLI test: PASS"
