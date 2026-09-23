#!/usr/bin/env bash
# clpeak test_package runner — 2 assertions:
#   1. clpeak --version   -> prints version, exit 0
#   2. clpeak (no args)   -> no OpenCL platform: "no platforms found", exit 0
# 注: 手动捕获 $? 与 set -e 冲突，用 -u -o pipefail（agent-browser/test.sh 先例）
set -uo pipefail

CLPEAK_BIN="${1:?usage: test_clpeak.sh <clpeak-binary>}"
failed=0

# --- assertion 1: --version ---
ver_out="$("$CLPEAK_BIN" --version 2>&1)"
ver_rc=$?
echo "clpeak --version => rc=$ver_rc"
echo "$ver_out"
if [ $ver_rc -ne 0 ]; then
    echo "FAIL: clpeak --version exited $ver_rc"
    failed=1
fi

# --- assertion 2: plain run (no OpenCL platform tolerated) ---
run_out="$("$CLPEAK_BIN" 2>&1)"
run_rc=$?
echo "clpeak (no args) => rc=$run_rc"
echo "$run_out"
if [ $run_rc -ne 0 ]; then
    echo "FAIL: clpeak (no args) exited $run_rc"
    failed=1
fi

if [ $failed -ne 0 ]; then
    echo "clpeak test_package: FAILED"
    exit 1
fi
echo "clpeak test_package: PASSED"
exit 0
