#!/bin/bash
# test_package/test.sh — openocd 消费者测试
# 验证 openocd 二进制存在、可执行且 --version 输出正确

set -euo pipefail
BIN_DIR="$1"
OPENOCD_BIN="${BIN_DIR}/bin/openocd"

echo "=== openocd test ==="
echo "Testing binary: ${OPENOCD_BIN}"

if [ ! -f "${OPENOCD_BIN}" ]; then
    echo "FAIL: openocd binary not found"
    exit 1
fi
if [ ! -x "${OPENOCD_BIN}" ]; then
    echo "FAIL: openocd binary not executable"
    exit 1
fi

VERSION_OUT=$("${OPENOCD_BIN}" --version 2>&1) || {
    echo "FAIL: openocd --version exited non-zero"
    exit 1
}

echo "${VERSION_OUT}" | grep -q "Open On-Chip Debugger" || {
    echo "FAIL: openocd --version output missing 'Open On-Chip Debugger'"
    exit 1
}
echo "${VERSION_OUT}" | grep -q "0.12.0" || {
    echo "FAIL: openocd --version output missing version 0.12.0"
    exit 1
}

echo "PASS: openocd --version validated"
exit 0
