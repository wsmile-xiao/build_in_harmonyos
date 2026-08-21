#!/bin/sh
# test_account_utils.sh — account-utils test_package 测试脚本
# 验证 chfn/chsh 可执行 + 实际版本/用法输出（R34：实质调用被测包）
#
# 用法: sh test_account_utils.sh <bin_dir>
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
CHFN="$BIN_DIR/chfn"
CHSH="$BIN_DIR/chsh"

echo "== 1. 可执行性检查 =="
if [ ! -x "$CHFN" ] || [ ! -x "$CHSH" ]; then
    echo "FAIL: chfn/chsh not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（用法/版本输出）=="
# chfn/chsh 无交互终端时以错误码退出，但会输出用法 → 捕获输出判断
if OUT=$("$CHFN" --help 2>&1) || OUT=$("$CHSH" --help 2>&1); then
    :
else
    # 退出码非 0 时用法输出应含命令名
    OUT=$( { "$CHFN" 2>&1 || true; } )
fi
if echo "$OUT" | grep -qi "chfn\|chsh\|usage"; then
    echo "OK: account-utils commands ran (usage output detected)"
else
    echo "FAIL: account-utils did not produce expected output: $OUT" >&2
    exit 1
fi
