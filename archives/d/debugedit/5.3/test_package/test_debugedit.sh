#!/bin/sh
# debugedit test_package 消费者测试
# 验证 debugedit CLI 工具存在 + debugedit --version 运行
set -e

BIN_DIR="$1"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin dir not provided or missing: $BIN_DIR"
    exit 1
fi

for t in debugedit debugedit-classify-ar sepdebugcrcfix; do
    if [ ! -x "$BIN_DIR/$t" ]; then
        echo "FAIL: missing CLI tool: $t"
        exit 1
    fi
done
echo "OK: debugedit/debugedit-classify-ar/sepdebugcrcfix present"

"$BIN_DIR/debugedit" --version >/dev/null 2>&1
echo "OK: debugedit --version runs"

echo "debugedit test_package PASS"
