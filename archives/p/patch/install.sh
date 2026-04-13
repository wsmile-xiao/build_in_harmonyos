#!/bin/sh
# install-patch-2.7.6.sh — GNU patch 2.7.6 预编译包安装脚本
# 目标: HarmonyOS/OpenHarmony aarch64

set -e

PREFIX="${1:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 如果从 tar.gz 解压运行，SCRIPT_DIR 就是解压目录
# 如果从归档目录运行，需要指向 packaging 子目录
if [ -d "$SCRIPT_DIR/bin" ]; then
    SRC="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/packaging/pkg-patch-2.7.6" ]; then
    SRC="$SCRIPT_DIR/packaging/pkg-patch-2.7.6"
else
    echo "错误: 找不到 bin/ 目录" >&2
    exit 1
fi

echo "安装 GNU patch 2.7.6 → $PREFIX"

mkdir -p "$PREFIX/bin"

# 安装二进制
cp "$SRC/bin/patch" "$PREFIX/bin/patch"
chmod 755 "$PREFIX/bin/patch"

# 验证
if "$PREFIX/bin/patch" --version >/dev/null 2>&1; then
    echo "✅ patch 2.7.6 安装成功: $PREFIX/bin/patch"
else
    echo "❌ 安装验证失败" >&2
    exit 1
fi
