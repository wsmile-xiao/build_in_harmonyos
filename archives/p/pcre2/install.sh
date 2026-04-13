#!/bin/sh
# PCRE2 安装脚本 for HarmonyOS
# 用法：sh install.sh [版本号] [安装路径]
# 默认：sh install.sh 10.40 $HOME/usr/local

PACKAGE_NAME="pcre2"
DEFAULT_VERSION="10.40"
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
PACKAGE_FILE="$VERSION_DIR/packaging/pcre2-$VERSION-harmonyos-aarch64.tar.gz"
if [ ! -f "$PACKAGE_FILE" ]; then
    PACKAGE_FILE="$VERSION_DIR/pcre2-$VERSION-harmonyos-aarch64.tar.gz"
fi

if [ ! -f "$PACKAGE_FILE" ]; then
    echo "❌ 错误：找不到预编译包"
    echo "预期位置：$VERSION_DIR/packaging/pcre2-$VERSION-harmonyos-aarch64.tar.gz"
    exit 1
fi

# 解压到临时目录
TMP_DIR="$HOME/tmp/pcre2-install-$$"
mkdir -p "$TMP_DIR"
echo "解压预编译包..."
tar xzf "$PACKAGE_FILE" -C "$TMP_DIR"

# 安装库文件
mkdir -p "$INSTALL_DIR/lib"
for lib in libpcre2-8.a libpcre2-16.a libpcre2-32.a libpcre2-posix.a; do
    if [ -f "$TMP_DIR/lib/$lib" ]; then
        cp "$TMP_DIR/lib/$lib" "$INSTALL_DIR/lib/"
        echo "✅ 已安装静态库: $INSTALL_DIR/lib/$lib"
    fi
done

# 安装动态库（如果有）
for lib in libpcre2-8.so libpcre2-16.so libpcre2-32.so libpcre2-posix.so; do
    if [ -f "$TMP_DIR/lib/$lib" ]; then
        cp "$TMP_DIR/lib/$lib"* "$INSTALL_DIR/lib/"
        echo "✅ 已安装动态库: $INSTALL_DIR/lib/$lib"
    fi
done

# 安装头文件
mkdir -p "$INSTALL_DIR/include"
for header in pcre2.h pcre2posix.h; do
    if [ -f "$TMP_DIR/include/$header" ]; then
        cp "$TMP_DIR/include/$header" "$INSTALL_DIR/include/"
        echo "✅ 已安装头文件: $INSTALL_DIR/include/$header"
    fi
done

# 安装 pkg-config 文件
mkdir -p "$INSTALL_DIR/lib/pkgconfig"
if [ -d "$TMP_DIR/lib/pkgconfig" ]; then
    for pc in libpcre2-8.pc libpcre2-16.pc libpcre2-32.pc libpcre2-posix.pc; do
        if [ -f "$TMP_DIR/lib/pkgconfig/$pc" ]; then
            # 修正 prefix 路径
            sed "s|^prefix=.*|prefix=$INSTALL_DIR|" "$TMP_DIR/lib/pkgconfig/$pc" > "$INSTALL_DIR/lib/pkgconfig/$pc"
            echo "✅ 已安装 pkg-config: $INSTALL_DIR/lib/pkgconfig/$pc"
        fi
    done
fi

# 清理临时目录
rm -rf "$TMP_DIR"

echo ""
echo "✅ 安装完成！"
echo ""
echo "已安装内容："
ls -la "$INSTALL_DIR/lib/libpcre2*"
ls -la "$INSTALL_DIR/include/pcre2*"
echo ""
echo "使用方法（编译链接）："
echo "  8位编码: -lpcre2-8"
echo "  16位编码: -lpcre2-16"
echo "  32位编码: -lpcre2-32"
echo "  POSIX API: -lpcre2-posix"
echo ""
echo "示例编译命令："
echo "  clang -o myapp myapp.c -I$INSTALL_DIR/include -L$INSTALL_DIR/lib -lpcre2-8"
echo ""
echo "使用 pkg-config："
echo "  pkg-config --cflags --libs pcre2-8"