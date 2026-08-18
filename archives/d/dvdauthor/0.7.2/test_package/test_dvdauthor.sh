#!/bin/sh
# test_dvdauthor.sh — dvdauthor test_package 测试脚本
# 验证 dvdauthor 可执行 + 实际版本/用法输出（R34：实质调用被测包）
#
# 用法: sh test_dvdauthor.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
DVDAUTHOR="$BIN_DIR/dvdauthor"

echo "== 1. 可执行性检查 =="
if [ ! -x "$DVDAUTHOR" ]; then
    echo "FAIL: dvdauthor not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（版本/用法输出）=="
# dvdauthor 无参数/无效参数时输出用法或版本 → 捕获输出判断
OUT=$("$DVDAUTHOR" --help 2>&1 || "$DVDAUTHOR" --version 2>&1 || true)
if echo "$OUT" | grep -qiE "dvdauthor|usage|version"; then
    echo "OK: dvdauthor ran successfully (usage/version output detected)"
else
    echo "FAIL: dvdauthor did not produce expected output: $OUT" >&2
    exit 1
fi
