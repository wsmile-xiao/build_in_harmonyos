#!/bin/sh
# test_tofrodos.sh — tofrodos test_package 测试脚本
# 验证 fromdos/todos 可执行 + 实际文本行结束符转换（R34：实质调用被测包）
#
# 用法: sh test_tofrodos.sh <bin_dir> [<tmp_dir>]
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir> [<tmp_dir>]" >&2
    exit 2
fi
BIN_DIR="$1"
FROMDOS="$BIN_DIR/fromdos"
TODOS="$BIN_DIR/todos"
# CR：POSIX sh 无 $'...' 引用（bash/ksh 专有），用 $(printf '\r') 生成
CR=$(printf '\r')

echo "== 1. 可执行性检查 =="
if [ ! -x "$FROMDOS" ] || [ ! -x "$TODOS" ]; then
    echo "FAIL: fromdos/todos not executable" >&2
    exit 1
fi

echo "== 2. 实际转换验证（todos: Unix→DOS；fromdos: DOS→Unix）=="
TMP_DIR="${2:-.}/tofrodos-test"
mkdir -p "$TMP_DIR"
printf 'line1\nline2\n' > "$TMP_DIR/unix.txt"

"$TODOS" "$TMP_DIR/unix.txt" 2>/dev/null
if ! grep -q "$CR" "$TMP_DIR/unix.txt"; then
    echo "FAIL: todos did not add CRLF line endings" >&2
    exit 1
fi

"$FROMDOS" "$TMP_DIR/unix.txt" 2>/dev/null
if grep -q "$CR" "$TMP_DIR/unix.txt"; then
    echo "FAIL: fromdos did not remove CRLF line endings" >&2
    exit 1
fi

echo "OK: fromdos/todos round-trip conversion verified"
rm -rf "$TMP_DIR"
