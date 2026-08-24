#!/bin/sh
# test_jot.sh — athena-jot test_package 测试脚本
# 验证 jot 可执行 + 实际运行（R34：实质调用被测包——jot 生成数字序列）
#
# 用法: sh test_jot.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
JOT="$BIN_DIR/jot"

echo "== 1. 可执行性检查 =="
if [ ! -x "$JOT" ]; then
    echo "FAIL: jot not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（jot 3——生成 1 2 3 数字序列）=="
# 保留退出码（不吞）——崩溃/失败即 FAIL
if ! OUT=$("$JOT" 3 2>&1); then
    echo "FAIL: jot failed (rc=$?): $OUT" >&2
    exit 1
fi
# 强断言：jot 3 输出换行分隔的 3 行数字（1/2/3）——行数 + 首尾数字
# 精确匹配（宽泛 grep 会把崩溃输出误判为通过）
if [ "$(echo "$OUT" | wc -l)" -ge 3 ] \
        && echo "$OUT" | grep -qE "^1$" \
        && echo "$OUT" | grep -qE "^3$"; then
    echo "OK: jot ran successfully (sequence 1..3 generated)"
else
    echo "FAIL: jot did not produce expected output: $OUT" >&2
    exit 1
fi
