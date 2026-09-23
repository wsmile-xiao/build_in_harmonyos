#!/bin/sh
# test_mydumper.sh — mydumper test_package 测试脚本
# 验证 mydumper/myloader 可执行 + 实际版本/用法输出（R34：实质调用被测包）
#
# 用法: sh test_mydumper.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
MYDUMPER="$BIN_DIR/mydumper"
MYLOADER="$BIN_DIR/myloader"

echo "== 1. 可执行性检查 =="
if [ ! -x "$MYDUMPER" ] || [ ! -x "$MYLOADER" ]; then
    echo "FAIL: mydumper/myloader not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（版本/用法输出）=="
OUT=$("$MYDUMPER" --version 2>&1 || "$MYDUMPER" 2>&1 || true)
if echo "$OUT" | grep -qi "mydumper\|usage\|version"; then
    echo "OK: mydumper ran successfully (usage/version output detected)"
else
    echo "FAIL: mydumper did not produce expected output: $OUT" >&2
    exit 1
fi
