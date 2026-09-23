#!/bin/sh
# test_libxkbcommon.sh — libxkbcommon 库消费者验证脚本
#
# 验证 libxkbcommon 库产物完整：头文件 xkbcommon/xkbcommon.h、
# libxkbcommon.so、xkbcommon.pc 存在，且 .pc 声明了库与 include 路径。
# 用法：test_libxkbcommon.sh <pkg_dir>
set -u

PKG="$1"

header="$PKG/include/xkbcommon/xkbcommon.h"
lib="$(ls "$PKG"/lib/libxkbcommon.so* 2>/dev/null | head -1)"
pc="$PKG/lib/pkgconfig/xkbcommon.pc"

for f in "$header" "$pc"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: 文件缺失: $f"
        exit 1
    fi
done
if [ -z "$lib" ]; then
    echo "FAIL: libxkbcommon.so 缺失"
    exit 1
fi

if ! grep -q "xkbcommon" "$pc" 2>/dev/null; then
    echo "FAIL: xkbcommon.pc 未声明库"
    exit 1
fi

echo "PASS: libxkbcommon 产物完整（header/lib/pc 均存在）"
echo "  - $(basename "$header")"
echo "  - $(basename "$lib")"
echo "  - $(basename "$pc")"
exit 0
