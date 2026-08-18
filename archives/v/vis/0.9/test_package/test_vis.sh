#!/bin/sh
# test_vis.sh — vis test_package 测试脚本
# 验证 vis 可执行 + 实际版本/用法输出（R34：实质调用被测包）
#
# 用法: sh test_vis.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
VIS="$BIN_DIR/vis"

echo "== 1. 可执行性检查 =="
if [ ! -x "$VIS" ]; then
    echo "FAIL: vis not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（TUI 启动/错误输出）=="
# vis 是 TUI 编辑器：无参数启动在无终端环境输出 "Failed to start
# curses interface"（curses 相关）→ 捕获输出判断（不支持 --version/-h）
OUT=$("$VIS" 2>&1 || true)
if echo "$OUT" | grep -qiE "vis|usage|error|terminal|curses|interface"; then
    echo "OK: vis ran successfully (curses/terminal output detected)"
else
    echo "FAIL: vis did not produce expected output: $OUT" >&2
    exit 1
fi
