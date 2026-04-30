#!/bin/bash
# libiio 0.26 安装脚本
# 用法: ./install.sh [PREFIX]
# 默认 PREFIX: ~/usr/local

PREFIX="${1:-$HOME/usr/local}"

echo "安装 libiio 0.26 到 $PREFIX..."

# 创建目录
mkdir -p "$PREFIX/lib/pkgconfig"
mkdir -p "$PREFIX/include"

# 解压预编译包
tar -xzf libiio-0.26-ohos-aarch64.tar.gz -C "$PREFIX"

echo "安装完成！"
echo "库文件: $PREFIX/lib/libiio.so"
echo "头文件: $PREFIX/include/iio.h"
echo "pkg-config: $PREFIX/lib/pkgconfig/libiio.pc"

# 验证
if [ -f "$PREFIX/lib/libiio.so" ]; then
    echo "✅ 验证成功"
else
    echo "❌ 验证失败"
fi