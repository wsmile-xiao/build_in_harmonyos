#!/bin/sh
# test_package/test.sh — smoke test for the nethogs binary.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -eu

echo "[test] nethogs -V"
if ! nethogs -V 2>&1 | grep -q "0.8.8"; then
    echo "FAIL: nethogs -V did not report version 0.8.8"
    exit 1
fi
echo "OK: nethogs -V reports version 0.8.8"

echo "[test] nethogs -h"
if ! nethogs -h 2>&1 | grep -q "usage"; then
    echo "FAIL: nethogs -h did not print usage"
    exit 1
fi
echo "OK: nethogs -h prints usage"

echo "test_package PASSED"

# HMBS 机器门禁要求：test_package 结束后必须产出一行合法
# HMBS_TEST_PACKAGE_RESULT=... JSON 标记。discovered/passedCount 必填，
# 为 test_package 真实用例计数（本脚本含 -V / -h 共 2 个断言）。
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":2,"passedCount":2}\n'