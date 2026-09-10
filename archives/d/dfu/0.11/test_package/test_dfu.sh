#!/bin/sh
# dfu-util test_package 消费者测试
# 验证三个 CLI 工具存在 + dfu-util --version + dfu-suffix 文件操作（无需 USB 设备）
set -e

BIN_DIR="$1"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin dir not provided or missing: $BIN_DIR"
    exit 1
fi

# 1) 三个 CLI 工具存在
for t in dfu-util dfu-suffix dfu-prefix; do
    if [ ! -x "$BIN_DIR/$t" ]; then
        echo "FAIL: missing CLI tool: $t"
        exit 1
    fi
done
echo "OK: dfu-util/dfu-suffix/dfu-prefix present"

# 2) dfu-util --version（验证可执行 + libusb 链接）
"$BIN_DIR/dfu-util" --version >/dev/null 2>&1
echo "OK: dfu-util --version runs"

# 3) dfu-suffix 文件操作（DFU 文件格式，无需 USB 设备）
TMPF=$(mktemp /storage/Users/currentUser/tmp/dfu_test_XXXXXX 2>/dev/null || mktemp ./dfu_test_XXXXXX)
trap 'rm -f "$TMPF"' EXIT
# 构造 32 字节固件
head -c 32 /dev/zero > "$TMPF"
# 加后缀
"$BIN_DIR/dfu-suffix" -a "$TMPF" -v 0483 -p df11 -d 0000 >/dev/null 2>&1
# 校验后缀
"$BIN_DIR/dfu-suffix" -c "$TMPF" >/dev/null 2>&1
echo "OK: dfu-suffix add + check suffix"

echo "dfu test_package PASS"
