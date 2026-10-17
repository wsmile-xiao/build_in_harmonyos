#!/bin/sh
# test_bashacks.sh — bashacks test_package 测试脚本
# 验证 bashacks.sh 函数库可 source 并调用 bh_* 函数（R34：实质调用被测包）
#
# 用法: sh test_bashacks.sh <lib_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <lib_dir>" >&2
    exit 2
fi
LIB_DIR="$1"
LIB="$LIB_DIR/bashacks.sh"

echo "== 1. 函数库存在性检查 =="
if [ ! -f "$LIB" ]; then
    echo "FAIL: bashacks.sh not found" >&2
    exit 1
fi

echo "== 2. 实际调用（source bashacks.sh + 调用 bh_bin2dec 函数）=="
# 保留退出码（不吞）——显式 rc 检查（RC=0 默认值——set -u 安全——
# 吸取 backupninja 审查 P2 教训）
RC=0
OUT=$(bash -c '. "$1" && bh_bin2dec 101' _ "$LIB" 2>&1) || RC=$?
if [ "$RC" -ne 0 ]; then
    echo "FAIL: bashacks function call failed (rc=$RC): $OUT" >&2
    exit 1
fi
# 强断言：bh_bin2dec 101 输出 5（二进制转十进制——宽泛 grep 会把
# 崩溃输出误判为通过）
if echo "$OUT" | grep -qE "^5$"; then
    echo "OK: bashacks function library ran successfully (bh_bin2dec 101=5)"
else
    echo "FAIL: bashacks did not produce expected output: $OUT" >&2
    exit 1
fi
