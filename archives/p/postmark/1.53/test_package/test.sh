#!/usr/bin/env bash
# test_package consumer test for postmark.
# Runs the installed `postmark` binary with a minimal config file
# (small file count / small transaction count) to verify the benchmark
# executes end-to-end and produces the verbose report.
set -euo pipefail

# Use $TMPDIR (OHOS /tmp is read-only); fall back to HOME/tmp.
WORK="${TMPDIR:-$HOME/tmp}/postmark-test"
mkdir -p "$WORK"
CFG="$WORK/postmark.cfg"

echo "--- postmark consumer verification ---"

# 1. minimal benchmark config: 20 files, 512..1024 bytes, 10 transactions, 1 subdir
#    (file count must exceed transaction count, else postmark reports "out of files!")
cat > "$CFG" <<EOF
set location $WORK
set number 20
set size 512 1024
set transactions 10
set subdirectories 1
set buffering false
run
quit
EOF

out=$(postmark "$CFG" 2>&1) || rc=$?
rc="${rc:-0}"
echo "$out" | grep -q "PostMark v1.5" || {
  echo "FAIL: unexpected banner [$out]"; exit 1; }
echo "PASS 1: banner printed"

# 2. report must contain the transaction summary line (per-second format) and the Files report block
#    (pattern-match any non-zero per-second rate; literal "10" is timing-sensitive)
echo "$out" | grep -Eq 'transactions \([1-9][0-9]* per second\)' || {
  echo "FAIL: report missing transactions summary [$out]"; exit 1; }
echo "PASS 2: report contains transaction summary"

echo "$out" | grep -q "Files:" || {
  echo "FAIL: report missing Files block [$out]"; exit 1; }
echo "PASS 3: report contains Files block"

[ "$rc" = "0" ] || { echo "FAIL: postmark exit=$rc"; exit 1; }
echo "PASS 4: postmark exit code 0"

rm -rf "$WORK"
echo "test postmark 1.53: 4/4 checks PASS"
exit 0
