#!/bin/bash
# libtommath 1.3.0 安装脚本
# OpenHarmony aarch64 预编译包安装

set -e

# 默认安装前缀
PREFIX="${PREFIX:-$HOME/usr/local}"
ARCHIVE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== libtommath 1.3.0 安装脚本 ==="
echo "安装目标: $PREFIX"
echo ""

# 创建目录
mkdir -p "$PREFIX/lib"
mkdir -p "$PREFIX/include"

# 安装静态库
if [ -f "$ARCHIVE_DIR/lib/libtommath.a" ]; then
    cp "$ARCHIVE_DIR/lib/libtommath.a" "$PREFIX/lib/"
    echo "已安装: $PREFIX/lib/libtommath.a"
else
    echo "错误: 找不到 libtommath.a"
    exit 1
fi

# 安装头文件
if [ -f "$ARCHIVE_DIR/include/tommath.h" ]; then
    cp "$ARCHIVE_DIR/include/tommath.h" "$PREFIX/include/"
    echo "已安装: $PREFIX/include/tommath.h"
else
    echo "错误: 找不到 tommath.h"
    exit 1
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法:"
echo "  1. 在代码中包含: #include <tommath.h>"
echo "  2. 编译时链接: -ltommath"
echo "  3. 如果需要指定路径: -I$PREFIX/include -L$PREFIX/lib"
echo ""
echo "示例编译命令:"
echo "  cc -I$PREFIX/include your_program.c -L$PREFIX/lib -ltommath -o your_program"
echo ""

exit 0