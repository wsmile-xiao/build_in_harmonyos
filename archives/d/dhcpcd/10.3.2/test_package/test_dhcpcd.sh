#!/bin/sh
# dhcpcd test_package 消费者测试
# 验证 dhcpcd 二进制存在 + --version 运行（无网络环境的构建/链接验证）
set -e

BIN_DIR="$1"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin dir not provided or missing: $BIN_DIR"
    exit 1
fi

if [ ! -x "$BIN_DIR/dhcpcd" ]; then
    echo "FAIL: dhcpcd binary missing in $BIN_DIR"
    exit 1
fi
echo "OK: dhcpcd present in $BIN_DIR"

"$BIN_DIR/dhcpcd" --version >/dev/null 2>&1
echo "OK: dhcpcd --version runs"

echo "dhcpcd test_package PASS"
