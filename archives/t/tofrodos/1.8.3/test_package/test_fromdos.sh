#!/bin/sh
# test_fromdos.sh — tofrodos test_package 测试脚本
# 验证 fromdos/todos 可执行 + CRLF→LF 实际转换（R34：实质调用被测包）
#
# 用法: sh test_fromdos.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
FROMDOS="$BIN_DIR/fromdos"
TODOS="$BIN_DIR/todos"

echo "== 1. 可执行性检查 =="
"$FROMDOS" -h >/dev/null 2>&1 || "$FROMDOS" --help >/dev/null 2>&1 || true
"$FROMDOS" -h >/dev/null 2>&1 || "$FROMDOS" --help >/dev/null 2>&1 || { echo "FAIL: fromdos not executable" >&2; exit 1; }
"$TODOS" -h >/dev/null 2>&1 || "$TODOS" --help >/dev/null 2>&1 || { echo "FAIL: todos not executable" >&2; exit 1; }

echo "== 2. 实际 CRLF→LF 转换 =="
TMP_FILE=$(mktemp)
printf 'line1\r\nline2\r\n' > "$TMP_FILE"
"$FROMDOS" "$TMP_FILE"
if grep -q "$(printf '\r')" "$TMP_FILE"; then
    echo "FAIL: CRLF still present after fromdos" >&2
    rm -f "$TMP_FILE"
    exit 1
fi
rm -f "$TMP_FILE"
echo "OK: fromdos converted CRLF→LF"
