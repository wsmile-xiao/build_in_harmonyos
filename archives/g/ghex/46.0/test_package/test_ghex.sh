#!/bin/sh
# test_ghex.sh — ghex 46.0 test_package 消费者验证
#
# 参数：$1 = ghex 二进制路径
# 退出码：0 = 全部通过，非 0 = 失败
set -e

GHEX_BIN="$1"
if [ -z "$GHEX_BIN" ]; then
    echo "FAIL: missing ghex binary path"
    exit 1
fi

if [ ! -f "$GHEX_BIN" ]; then
    echo "FAIL: ghex binary not found: $GHEX_BIN"
    exit 1
fi

if [ ! -s "$GHEX_BIN" ]; then
    echo "FAIL: ghex binary is empty: $GHEX_BIN"
    exit 1
fi
echo "PASS 1/4: ghex binary exists ($(wc -c < "$GHEX_BIN") bytes)"

MAGIC=$(od -An -tx1 -N4 "$GHEX_BIN" | tr -d ' ')
if [ "$MAGIC" != "7f454c46" ]; then
    echo "FAIL: not an ELF (magic=$MAGIC)"
    exit 1
fi
echo "PASS 2/4: ELF magic OK"

HEADER=$(readelf -h "$GHEX_BIN" 2>/dev/null)
echo "$HEADER" | grep -q "AArch64" || { echo "FAIL: readelf -h missing AArch64"; exit 1; }
echo "$HEADER" | grep -q "ELF64" || { echo "FAIL: readelf -h missing ELF64"; exit 1; }
echo "PASS 3/4: readelf -h shows AArch64 + ELF64"

DYNAMIC=$(readelf -d "$GHEX_BIN" 2>/dev/null)
for lib in libgtkhex-4.so libgtk-4.so libadwaita-1.so; do
    echo "$DYNAMIC" | grep -q "$lib" || { echo "FAIL: readelf -d missing $lib"; exit 1; }
done
echo "PASS 4/4: readelf -d links GTK4/adwaita/gtkhex"

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_ghex.sh","discovered":4,"passedCount":4}'
exit 0
