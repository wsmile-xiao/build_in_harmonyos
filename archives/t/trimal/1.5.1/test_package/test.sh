#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the installed trimal package.
#
# Runs inside the conanrun environment (PATH contains the installed bin/).
# Covers: version smoke, automatic (-nogaps) and manual (-gt) trimming with
# expected-output diffs, a negative control, and readal/statal statistics.
# 10 assertions total.
#
# All scratch files are created in a private temporary directory: Conan may run
# this script in place (cwd = the recipe's test_package/ folder), and the test
# must never write into the recipe tree.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
scratch_root="${TMPDIR:-$HOME/tmp}"
mkdir -p "$scratch_root"
workdir="$(mktemp -d "$scratch_root/trimal-test.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT INT TERM
cp "$here/tiny.fasta" "$here/expected_nogaps.fasta" "$here/expected_gt.fasta" "$workdir/"
cd "$workdir"

fail() { echo "FAIL: $1" >&2; exit 1; }

# ── 1) version smoke ───────────────────────────────────────────────────────
trimal --version > version.out 2>&1
grep -q "trimAl v1\.5" version.out || fail "trimal --version did not report trimAl v1.5"

# ── 2) -nogaps drops every column containing at least one gap ──────────────
trimal -in tiny.fasta -out out_nogaps.fasta -nogaps
diff -u expected_nogaps.fasta out_nogaps.fasta > nogaps.diff 2>&1 \
    || fail "-nogaps output differs from expected_nogaps.fasta"

# ── 3) manual gap-threshold trimming (-gt 0.6) ─────────────────────────────
trimal -in tiny.fasta -out out_gt.fasta -gt 0.6
diff -u expected_gt.fasta out_gt.fasta > gt.diff 2>&1 \
    || fail "-gt 0.6 output differs from expected_gt.fasta"

# ── 4) negative control: a missing input must abort with non-zero status ───
if trimal -in does_not_exist.fasta -out should_not_exist.fasta 2> neg.err; then
    fail "trimal accepted a missing input file (expected non-zero exit)"
fi
grep -q "ERROR" neg.err || fail "missing-input error message was not printed"

# ── 5) readal alignment statistics ─────────────────────────────────────────
readal -in tiny.fasta -info > readal.out
grep -q "Total sequences" readal.out || fail "readal output lacks 'Total sequences'"
awk '/Total sequences/ {v=$NF} END {exit !(v==4)}' readal.out \
    || fail "readal sequence count != 4"
awk '/Alignment length/ {v=$NF} END {exit !(v==5)}' readal.out \
    || fail "readal alignment length != 5"

# ── 6) statal per-column gap scores (col 1 -> 50%, col 2 -> 25%) ───────────
statal -in tiny.fasta -sgc > statal.out 2>&1
awk '$1==1 && $2==50 {f1=1} END {exit !f1}' statal.out \
    || fail "statal column 1 gap score != 50%"
awk '$1==2 && $2==25 {f2=1} END {exit !f2}' statal.out \
    || fail "statal column 2 gap score != 25%"

echo "PASS: trimal test_package (10 assertions)"
