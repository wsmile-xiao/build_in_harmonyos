#!/bin/sh
# CLI test for yices tools: yices-smt2 on a tiny UNSAT instance.
# $1 = package bin dir.
set -e

BINDIR="$1"
YICES_SMT2="${BINDIR:+$BINDIR/}yices-smt2"

work="${TMPDIR:-.}/yices_cli_test.$$"
mkdir -p "$work"
cd "$work"
trap 'cd /; rm -rf "$work"' EXIT

cat > unsat.smt2 <<'EOF'
(set-logic QF_LIA)
(declare-const x Int)
(assert (> x 0))
(assert (< x 0))
(check-sat)
EOF

out=$("$YICES_SMT2" unsat.smt2)
echo "$out"
echo "$out" | grep -q "unsat" || { echo "FAIL: expected unsat"; exit 1; }

echo "yices CLI test: PASS"
