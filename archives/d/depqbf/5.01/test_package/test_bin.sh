#!/bin/sh
# test_package/test_bin.sh — validate the packaged `depqbf` CLI binary.
# Usage: test_bin.sh <fixture-dir>
# Runs in conanrun env (PATH includes the packaged bin/).
set -eu

FIX="${1:?fixture dir required}"
TMPD="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPD"

echo "[bin] depqbf --version"
depqbf --version || true

echo "[bin] depqbf --help"
depqbf --help > /dev/null

# Exit codes 10 (SAT) / 20 (UNSAT) are non-zero by design, so suspend
# `set -e` while capturing them.
set +e
depqbf "$FIX/sat.qdimacs" > "$TMPD/depqbf_sat.txt" 2>&1
rc_sat=$?
depqbf "$FIX/unsat.qdimacs" > "$TMPD/depqbf_unsat.txt" 2>&1
rc_unsat=$?
set -e

echo "[bin] sat exit=$rc_sat (want 10)"
cat "$TMPD/depqbf_sat.txt"
echo "[bin] unsat exit=$rc_unsat (want 20)"
cat "$TMPD/depqbf_unsat.txt"

if [ "$rc_sat" -ne 10 ]; then
    echo "FAIL: sat fixture exit=$rc_sat, want 10"
    exit 1
fi
if [ "$rc_unsat" -ne 20 ]; then
    echo "FAIL: unsat fixture exit=$rc_unsat, want 20"
    exit 1
fi
grep -q "SAT" "$TMPD/depqbf_sat.txt" || {
    echo "FAIL: sat stdout missing SAT"
    exit 1
}
grep -q "UNSAT" "$TMPD/depqbf_unsat.txt" || {
    echo "FAIL: unsat stdout missing UNSAT"
    exit 1
}
rm -f "$TMPD/depqbf_sat.txt" "$TMPD/depqbf_unsat.txt"
echo "All depqbf binary checks passed."
