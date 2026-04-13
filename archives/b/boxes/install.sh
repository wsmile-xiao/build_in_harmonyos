#!/bin/sh
# boxes 安装脚本 for HarmonyOS
# 用法：sh install.sh [版本号] [安装路径]
# 默认：sh install.sh 2.3.1 $HOME/usr/local

PACKAGE_NAME="boxes"
DEFAULT_VERSION="2.3.1"
DEFAULT_INSTALL_DIR="$HOME/usr/local"

VERSION="${1:-$DEFAULT_VERSION}"
INSTALL_DIR="${2:-$DEFAULT_INSTALL_DIR}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION_DIR="$SCRIPT_DIR/$VERSION"

echo "========================================"
echo "安装 $PACKAGE_NAME $VERSION for HarmonyOS"
echo "安装路径: $INSTALL_DIR"
echo "========================================"

# 检查版本目录
if [ ! -d "$VERSION_DIR" ]; then
    echo "❌ 错误：找不到版本目录 $VERSION_DIR"
    echo "可用版本："
    ls -d "$SCRIPT_DIR"/*/ 2>/dev/null | xargs -n1 basename
    exit 1
fi

# 检查预编译包
PACKAGE_FILE="$VERSION_DIR/packaging/boxes-$VERSION-harmonyos-aarch64.tar.gz"
if [ ! -f "$PACKAGE_FILE" ]; then
    # 尝试版本目录下的 tar.gz
    PACKAGE_FILE="$VERSION_DIR/boxes-$VERSION-harmonyos-aarch64.tar.gz"
fi

if [ ! -f "$PACKAGE_FILE" ]; then
    echo "❌ 错误：找不到预编译包"
    echo "预期位置：$VERSION_DIR/packaging/boxes-$VERSION-harmonyos-aarch64.tar.gz"
    exit 1
fi

# 解压到临时目录
TMP_DIR="$HOME/tmp/boxes-install-$$"
mkdir -p "$TMP_DIR"
echo "解压预编译包..."
tar xzf "$PACKAGE_FILE" -C "$TMP_DIR"

# 查找解压后的目录结构
if [ -f "$TMP_DIR/boxes" ]; then
    # 直接是二进制文件
    BIN_SRC="$TMP_DIR"
elif [ -d "$TMP_DIR/bin" ]; then
    # 有 bin 目录结构
    BIN_SRC="$TMP_DIR/bin"
else
    # 查找 boxes 二进制
    BIN_SRC=$(find "$TMP_DIR" -name "boxes" -type f | head -1 | xargs dirname)
fi

# 安装二进制
mkdir -p "$INSTALL_DIR/bin"
if [ -f "$BIN_SRC/boxes" ]; then
    cp "$BIN_SRC/boxes" "$INSTALL_DIR/bin/"
    chmod +x "$INSTALL_DIR/bin/boxes"
    echo "✅ 已安装: $INSTALL_DIR/bin/boxes"
else
    echo "❌ 错误：找不到 boxes 二进制"
    rm -rf "$TMP_DIR"
    exit 1
fi

# 安装配置文件
mkdir -p "$INSTALL_DIR/share/boxes"
CONFIG_FILE="$TMP_DIR/boxes-config"
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$INSTALL_DIR/share/boxes/"
    echo "✅ 已安装: $INSTALL_DIR/share/boxes/boxes-config"
elif [ -f "$BIN_SRC/../boxes-config" ]; then
    cp "$BIN_SRC/../boxes-config" "$INSTALL_DIR/share/boxes/"
    echo "✅ 已安装: $INSTALL_DIR/share/boxes/boxes-config"
else
    echo "⚠️ 警告：找不到 boxes-config 配置文件"
fi

# 预触发安全弹窗（HarmonyOS 特性）
echo "预触发二进制确认弹窗..."
"$INSTALL_DIR/bin/boxes" --version >/dev/null 2>&1 || true

# 清理临时目录
rm -rf "$TMP_DIR"

echo ""
echo "✅ 安装完成！"
echo ""
echo "验证安装："
echo "  $INSTALL_DIR/bin/boxes --version"
echo ""
echo "使用示例："
echo "  echo 'Hello World' | $INSTALL_DIR/bin/boxes"
echo ""
echo "如需全局使用，请将以下内容添加到 ~/.bashrc："
echo "  export PATH=\"$INSTALL_DIR/bin:\$PATH\""
echo "  export BOXES_CONFIG=\"$INSTALL_DIR/share/boxes/boxes-config\""