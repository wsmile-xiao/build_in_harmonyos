#!/bin/sh
# test_rpl.sh — rpl test_package 测试脚本
# 验证 rpl 可执行 + 实际文本替换（R34：实质调用被测包）
#
# 用法: sh test_rpl.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
RPL="$BIN_DIR/rpl"

echo "== 1. 可执行性检查 =="
"$RPL" --version >/dev/null 2>&1 || true

echo "== 2. 实际文本替换 =="
TMP_FILE=$(mktemp)
printf 'prefix oldtext suffix\n' > "$TMP_FILE"
"$RPL" -f oldtext newtext "$TMP_FILE"
if grep -q "newtext" "$TMP_FILE" && ! grep -q "oldtext" "$TMP_FILE"; then
    echo "OK: rpl replaced oldtext→newtext"
else
    echo "FAIL: replacement check failed" >&2
    rm -f "$TMP_FILE"
    exit 1
fi
rm -f "$TMP_FILE"
