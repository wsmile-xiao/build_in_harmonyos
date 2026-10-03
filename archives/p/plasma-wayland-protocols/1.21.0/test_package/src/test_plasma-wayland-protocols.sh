#!/bin/bash
# test_plasma-wayland-protocols.sh — pwp 数据包消费者验证脚本
#
# 验证 plasma-wayland-protocols 安装完整:
#   1. share/plasma-wayland-protocols/ 下 32 个 XML
#      (30 协议 + 2 向后兼容改名文件)
#   2. 两个改名兼容文件与原名文件内容一致
#   3. 协议 XML 含有效 <protocol name=...> 声明
# 用法: test_plasma-wayland-protocols.sh <pkg_dir>
set -euo pipefail

PKG="$1"
DIR="$PKG/share/plasma-wayland-protocols"

if [ ! -d "$DIR" ]; then
    echo "        [fail] 协议目录缺失: $DIR"
    exit 1
fi

# 1. XML 计数 = 32
count=$(find "$DIR" -maxdepth 1 -name '*.xml' | wc -l)
if [ "$count" -ne 32 ]; then
    echo "        [fail] 期望 32 个 XML,实得 $count"
    exit 1
fi

# 2. 改名兼容文件与原文件逐字节一致
for pair in \
    "zkde-screencast-unstable-v1.xml:screencast.xml" \
    "org-kde-plasma-virtual-desktop.xml:plasma-virtual-desktop.xml"; do
    orig="${pair%%:*}"; compat="${pair##*:}"
    if ! cmp -s "$DIR/$orig" "$DIR/$compat"; then
        echo "        [fail] 兼容改名文件内容不一致: $orig vs $compat"
        exit 1
    fi
done

# 3. 代表性协议含有效 protocol name 声明
name=$(sed -n 's/^<protocol name="\([^"]*\)">/\1/p' \
    "$DIR/plasma-window-management.xml" | head -1)
if [ -z "$name" ]; then
    echo "        [fail] plasma-window-management.xml 无 <protocol name=...> 声明"
    exit 1
fi

echo "        [ok] pwp 产物完整: 32 XML($name 等 30 协议 + 2 兼容改名,内容一致)"
exit 0
