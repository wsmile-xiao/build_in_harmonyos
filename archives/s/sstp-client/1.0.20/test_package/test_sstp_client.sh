#!/bin/sh
# test_sstp_client.sh — sstp-client test_package 测试脚本
# 验证 sstpc 可执行 + 实际版本/用法输出（R34：实质调用被测包）
#
# 用法: sh test_sstp_client.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
SSTPC="$BIN_DIR/sstpc"

echo "== 1. 可执行性检查 =="
if [ ! -x "$SSTPC" ]; then
    echo "FAIL: sstpc not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（版本/用法输出）=="
# sstpc 无 VPN 服务器时以错误码退出，但会输出用法 → 捕获输出判断
OUT=$("$SSTPC" --help 2>&1 || "$SSTPC" 2>&1 || true)
if echo "$OUT" | grep -qi "sstp\|usage"; then
    echo "OK: sstpc ran successfully (usage output detected)"
else
    echo "FAIL: sstpc did not produce expected output: $OUT" >&2
    exit 1
fi
