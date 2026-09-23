#!/bin/sh
# test_package consumer test for 2048.c.
# Runs the installed `2048` binary in its self-test mode (13 assertions) and
# checks --version output. Verifies a consumer can invoke the tool end to end.
export PATH="$PATH:/system/bin"

echo "--- 2048.c consumer verification ---"

# 1. version info
out1=$(2048 --version)
[ -n "$out1" ] || { echo "FAIL: --version produced no output"; exit 1; }
echo "PASS 1: --version -> $out1"

# 2. built-in upstream test suite: 13 assertions inside the binary
out2=$(2048 test)
rc=$?
[ "$rc" = "0" ] || { echo "FAIL: 2048 test exit=$rc"; exit 1; }
echo "$out2" | grep -q "All 13 tests executed successfully" || {
  echo "FAIL: unexpected self-test output [$out2]"; exit 1; }
echo "PASS 2: self-test -> $out2"

echo "test 2048.c 1.0.3: 2/2 checks PASS"
exit 0