#!/bin/sh
# test_itstool.sh — itstool test_package 测试脚本
# 验证 itstool 可执行 + 实际运行（R34：实质调用被测包）
#
# 用法: sh test_itstool.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
ITSTOOL="$BIN_DIR/itstool"

echo "== 1. 可执行性检查 =="
if [ ! -x "$ITSTOOL" ]; then
    echo "FAIL: itstool not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（--version）=="
# 保留退出码（不吞）——itstool 崩溃/失败时命令失败即报 FAIL
if ! OUT=$("$ITSTOOL" --version 2>&1); then
    echo "FAIL: itstool --version failed (rc=$?): $OUT" >&2
    exit 1
fi
# 强断言：版本号精确匹配（宽泛 grep 会把崩溃/报错输出误判为通过）
if echo "$OUT" | grep -qE "itstool.*2\.0\.7|2\.0\.7"; then
    echo "OK: itstool ran successfully (version 2.0.7 detected)"
else
    echo "FAIL: itstool did not produce expected output: $OUT" >&2
    exit 1
fi
