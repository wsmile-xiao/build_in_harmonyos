#!/bin/sh
# test_brightnessctl.sh — brightnessctl test_package 测试脚本
# 验证 brightnessctl 可执行 + 实际运行（R34：实质调用被测包）
#
# 用法: sh test_brightnessctl.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
BCTL="$BIN_DIR/brightnessctl"

echo "== 1. 可执行性检查 =="
if [ ! -x "$BCTL" ]; then
    echo "FAIL: brightnessctl not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（-v 版本输出）=="
# 保留退出码（不吞）——崩溃/失败即 FAIL
if ! OUT=$("$BCTL" -V 2>&1); then
    echo "FAIL: brightnessctl -V failed (rc=$?): $OUT" >&2
    exit 1
fi
# 强断言：版本号精确匹配（宽泛 grep 会把崩溃输出误判为通过）
if echo "$OUT" | grep -qE "brightnessctl.*0\.5\.1|0\.5\.1"; then
    echo "OK: brightnessctl ran successfully (version 0.5.1 detected)"
else
    echo "FAIL: brightnessctl did not produce expected output: $OUT" >&2
    exit 1
fi
