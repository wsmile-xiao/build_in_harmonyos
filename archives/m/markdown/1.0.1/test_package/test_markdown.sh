#!/bin/sh
# test_markdown.sh — markdown test_package 测试脚本
# 验证 markdown 可执行 + 实际 Markdown→HTML 转换（R34：实质调用被测包）
#
# 用法: sh test_markdown.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
MD="$BIN_DIR/markdown"

echo "== 1. 可执行性检查 =="
# Markdown.pl 1.0.1 无 --version/-v 选项，改用执行位直接判断（AI 检视 P1）
if [ ! -x "$MD" ]; then
    echo "FAIL: markdown not executable" >&2
    exit 1
fi

echo "== 2. 实际 Markdown→HTML 转换 =="
HTML=$(printf '**bold** and *em*\n\n# Title\n' | "$MD" 2>/dev/null || true)
if echo "$HTML" | grep -q "<h1>"; then
    echo "OK: markdown produced <h1>Title</h1>"
else
    echo "FAIL: no <h1> in output: $HTML" >&2
    exit 1
fi
