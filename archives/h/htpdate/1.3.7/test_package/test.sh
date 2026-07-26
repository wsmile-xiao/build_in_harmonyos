#!/bin/sh
# test_package/test.sh — smoke test for htpdate executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[step] htpdate -v (version check)"
htpdate -v
echo "[ok] version check passed"

echo "[step] htpdate -h (help output, non-zero exit is normal)"
htpdate -h >/dev/null 2>&1 || true
echo "[ok] help check completed"
