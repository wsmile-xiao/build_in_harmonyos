#!/bin/sh
# pstree 安装脚本
# 用法: sh install.sh [安装目录]

INSTALL_DIR="${1:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "安装 pstree 到 $INSTALL_DIR..."

# 创建目录
mkdir -p "$INSTALL_DIR/bin"
mkdir -p "$INSTALL_DIR/lib"

# 安装二进制文件
if [ -f "$SCRIPT_DIR/bin/pstree" ]; then
    cp "$SCRIPT_DIR/bin/pstree" "$INSTALL_DIR/bin/"
    chmod 755 "$INSTALL_DIR/bin/pstree"
    echo "✓ 已安装: $INSTALL_DIR/bin/pstree"
else
    echo "✗ 错误: 找不到 bin/pstree"
    exit 1
fi

echo ""
echo "安装完成！"
echo "验证: $INSTALL_DIR/bin/pstree --version"
