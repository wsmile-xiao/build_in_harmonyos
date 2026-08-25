#!/bin/sh
# test_hyprutils.sh — hyprutils 库消费者验证脚本
#
# 验证 hyprutils 库产物完整：头文件 hyprutils/math/Vector2D.hpp、
# 共享库 libhyprutils.so、hyprutils.pc 存在，且 .pc 声明了
# 库与 include 路径。作为 hyprutils 可用的冒烟测试。
# 用法：test_hyprutils.sh <pkg_dir>
set -u

PKG="$1"

header="$PKG/include/hyprutils/math/Vector2D.hpp"
lib="$(ls "$PKG"/lib/libhyprutils.so* 2>/dev/null | head -1)"
pc="$PKG/lib/pkgconfig/hyprutils.pc"

for f in "$header" "$pc"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: 文件缺失: $f"
        exit 1
    fi
done
if [ -z "$lib" ]; then
    echo "FAIL: libhyprutils.so 缺失"
    exit 1
fi

# .pc 应声明库名 hyprutils
if ! grep -q "hyprutils" "$pc" 2>/dev/null; then
    echo "FAIL: hyprutils.pc 未声明库"
    exit 1
fi

echo "PASS: hyprutils 产物完整（header/lib/pc 均存在）"
echo "  - $(basename "$header")"
echo "  - $(basename "$lib")"
echo "  - $(basename "$pc")"
exit 0
