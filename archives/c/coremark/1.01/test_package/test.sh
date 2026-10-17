#!/bin/sh
# test_package consumer test for coremark 1.01.
# Runs the installed `coremark` binary in its standard validation run and
# checks the observable self-check output. Verifies a consumer can invoke
# the benchmark end to end.
set -u
EXE="${COREMARK_EXE:-coremark}"

echo "--- coremark 1.01 consumer verification ---"

# validation run; iterations=0 lets coremark auto-tune to its >=10s window
out=$("$EXE" 0x3415 0x3415 0x66 0 7 1 2000 2>&1); rc=$?
[ "$rc" = "0" ] || { echo "FAIL: coremark validation run exit=$rc"; exit 1; }
echo "$out" | grep -q "Correct operation validated" || {
  echo "FAIL: unexpected validation output [$out]"; exit 1; }
echo "PASS: Correct operation validated -> $out" | head -3

echo "test coremark 1.01: validation PASS"
exit 0