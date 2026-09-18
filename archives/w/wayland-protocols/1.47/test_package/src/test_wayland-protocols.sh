#!/usr/bin/zsh
# test_wayland-protocols.sh — wayland-protocols data 包消费者验证脚本
#
# 验证 wayland-protocols XML 协议定义安装完整：wayland-protocols.pc
# 存在，且 .pc 声明的 pkgdatadir 目录下有 stable/ 协议 XML 文件。
# 用法：test_wayland-protocols.sh <pkg_dir>
set -euo pipefail

PKG="$1"

# data 包：.pc 在 share/pkgconfig（meson 默认）
pc=""
for sub in share/pkgconfig lib/pkgconfig; do
    if [ -f "$PKG/$sub/wayland-protocols.pc" ]; then
        pc="$PKG/$sub/wayland-protocols.pc"
        break
    fi
done
if [ -z "$pc" ]; then
    echo "        [fail] wayland-protocols.pc 缺失"
    exit 1
fi

# pkgdatadir 是变量表达式（${pc_sysrootdir}${datarootdir}/...），
# 必须用 pkg-config --variable 查询真实路径（grep 文件拿不到展开值）
PKGDATADIR=""
if command -v pkg-config >/dev/null 2>&1; then
    PKGDATADIR=$(PKG_CONFIG_PATH="$(dirname "$pc")" \
        pkg-config --variable=pkgdatadir wayland-protocols 2>/dev/null)
fi
if [ -z "$PKGDATADIR" ] || [ ! -d "$PKGDATADIR" ]; then
    # pkg-config 不可用时的 fallback：直接检查包内 share/wayland-protocols
    PKGDATADIR="$PKG/share/wayland-protocols"
fi
if [ ! -d "$PKGDATADIR" ]; then
    echo "        [fail] pkgdatadir 无效: $PKGDATADIR"
    exit 1
fi

# 检查 stable/ 协议 XML 存在（XML 在 stable/<protocol>/ 子目录下）
xml=$(ls "$PKGDATADIR"/stable/*/*.xml 2>/dev/null | head -1)
if [ -z "$xml" ]; then
    echo "        [fail] stable/ 协议 XML 缺失: $PKGDATADIR/stable/"
    exit 1
fi

echo "        [ok] wayland-protocols 产物完整（.pc + stable 协议 XML 均存在）"
echo "  - $(basename "$pc")"
echo "  - $(basename "$xml")"
exit 0
