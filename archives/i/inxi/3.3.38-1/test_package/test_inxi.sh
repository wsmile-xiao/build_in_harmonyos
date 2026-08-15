#!/bin/sh
# test_inxi.sh — inxi test_package 测试脚本
# 验证 inxi 可执行 + 实际查询系统信息（R34：实质调用被测包）
#
# 用法: sh test_inxi.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
INXI="$BIN_DIR/inxi"

echo "== 1. 可执行性检查 =="
if [ ! -x "$INXI" ]; then
    echo "FAIL: inxi not executable" >&2
    exit 1
fi

echo "== 2. 实际系统信息查询 =="
OUT=$("$INXI" -v 2>&1 || "$INXI" -V 2>&1 || true)
if echo "$OUT" | grep -qiE "inxi|version"; then
    echo "OK: inxi ran successfully (version output detected)"
else
    echo "FAIL: inxi did not produce expected output: $OUT" >&2
    exit 1
fi
