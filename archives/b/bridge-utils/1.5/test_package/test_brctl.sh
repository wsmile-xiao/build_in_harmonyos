#!/bin/sh
# test_brctl.sh — bridge-utils test_package 测试脚本
# 验证 brctl 可执行 + 实际运行（R34：实质调用被测包）
#
# 用法: sh test_brctl.sh <bin_dir>
set -eu

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
BRCTL="$BIN_DIR/brctl"

echo "== 1. 可执行性检查 =="
if [ ! -x "$BRCTL" ]; then
    echo "FAIL: brctl not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（-V 版本输出）=="
# 保留退出码（不吞）——崩溃/失败报 FAIL
if ! OUT=$("$BRCTL" -V 2>&1); then
    echo "FAIL: brctl -V failed (rc=$?): $OUT" >&2
    exit 1
fi
# 强断言：精确匹配 brctl -V 实际输出格式（源码 PACKAGE_NAME, PACKAGE_VERSION
# ——configure.in AC_INIT(bridge-utils, 1.5) → "bridge-utils, 1.5"）
if echo "$OUT" | grep -qE "bridge-utils, 1\.5"; then
    echo "OK: brctl ran successfully (version 1.5 detected)"
else
    echo "FAIL: brctl did not produce expected output: $OUT" >&2
    exit 1
fi