#!/bin/sh
# GNU libunistring 安装脚本 for HarmonyOS
# 用法：sh install.sh [版本号] [安装路径]
# 默认：sh install.sh 1.0 $HOME/usr/local

PACKAGE_NAME="libunistring"
DEFAULT_VERSION="1.0"
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
PACKAGE_FILE="$VERSION_DIR/packaging/libunistring-$VERSION-harmonyos-aarch64.tar.gz"
if [ ! -f "$PACKAGE_FILE" ]; then
    PACKAGE_FILE="$VERSION_DIR/libunistring-$VERSION-harmonyos-aarch64.tar.gz"
fi

if [ ! -f "$PACKAGE_FILE" ]; then
    echo "❌ 错误：找不到预编译包"
    echo "预期位置：$VERSION_DIR/packaging/libunistring-$VERSION-harmonyos-aarch64.tar.gz"
    exit 1
fi

# 解压到临时目录
TMP_DIR="$HOME/tmp/libunistring-install-$$"
mkdir -p "$TMP_DIR"
echo "解压预编译包..."
tar xzf "$PACKAGE_FILE" -C "$TMP_DIR"

# 安装库文件
mkdir -p "$INSTALL_DIR/lib"
if [ -f "$TMP_DIR/lib/libunistring.a" ]; then
    cp "$TMP_DIR/lib/libunistring.a" "$INSTALL_DIR/lib/"
    echo "✅ 已安装静态库: $INSTALL_DIR/lib/libunistring.a"
fi

if [ -f "$TMP_DIR/lib/libunistring.so.2.2.0" ]; then
    cp "$TMP_DIR/lib/libunistring.so.2.2.0" "$INSTALL_DIR/lib/"
    cd "$INSTALL_DIR/lib"
    rm -f libunistring.so libunistring.so.2
    ln -s libunistring.so.2.2.0 libunistring.so.2
    ln -s libunistring.so.2 libunistring.so
    cd "$SCRIPT_DIR"
    echo "✅ 已安装动态库: $INSTALL_DIR/lib/libunistring.so.2.2.0"
fi

# 安装头文件
mkdir -p "$INSTALL_DIR/include"
if [ -d "$TMP_DIR/include" ]; then
    for header in unitypes.h unistring.h uniconv.h unistdio.h unictype.h uninorm.h; do
        if [ -f "$TMP_DIR/include/$header" ]; then
            cp "$TMP_DIR/include/$header" "$INSTALL_DIR/include/"
            echo "✅ 已安装头文件: $INSTALL_DIR/include/$header"
        fi
    done
fi

# 安装 pkg-config 文件（如果有）
mkdir -p "$INSTALL_DIR/lib/pkgconfig"
if [ -d "$TMP_DIR/lib/pkgconfig" ]; then
    cp "$TMP_DIR/lib/pkgconfig/*.pc" "$INSTALL_DIR/lib/pkgconfig/" 2>/dev/null || true
fi

# 清理临时目录
rm -rf "$TMP_DIR"

echo ""
echo "✅ 安装完成！"
echo ""
echo "已安装内容："
ls -la "$INSTALL_DIR/lib/libunistring*"
ls -la "$INSTALL_DIR/include/unistring*"
echo ""
echo "使用方法（编译链接）："
echo "  静态链接: -lunistring"
echo "  动态链接: -lunistring (需设置 LD_LIBRARY_PATH)"
echo ""
echo "示例编译命令："
echo "  clang -o myapp myapp.c -I$INSTALL_DIR/include -L$INSTALL_DIR/lib -lunistring"