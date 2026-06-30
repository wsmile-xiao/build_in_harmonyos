#!/bin/bash
# mbedtls 2.28.10 预编译包安装脚本
# 自动生成 by openharmony-compile-agent

PREFIX=${1:-$HOME/usr/local}

echo "安装 mbedtls 2.28.10 到 $PREFIX..."

# 解压文件
tar xzf mbedtls-2.28.10-ohos-aarch64.tar.gz -C "$PREFIX"

# 设置 PKG_CONFIG_PATH
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH

# 验证安装
echo "验证安装..."
if [ -f "$PREFIX/lib/libmbedcrypto.a" ]; then
    echo "✅ libmbedcrypto.a 已安装"
else
    echo "❌ libmbedcrypto.a 缺失"
fi

if [ -f "$PREFIX/lib/libmbedtls.a" ]; then
    echo "✅ libmbedtls.a 已安装"
else
    echo "❌ libmbedtls.a 缺失"
fi

if [ -f "$PREFIX/lib/libmbedx509.a" ]; then
    echo "✅ libmbedx509.a 已安装"
else
    echo "❌ libmbedx509.a 缺失"
fi

if pkg-config --exists mbedtls; then
    echo "✅ pkg-config 可找到 mbedtls"
    echo "   版本: $(pkg-config --modversion mbedtls)"
else
    echo "⚠️  pkg-config 未配置，请设置 PKG_CONFIG_PATH"
fi

echo "安装完成！"
