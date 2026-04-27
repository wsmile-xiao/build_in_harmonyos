#!/bin/sh
# CUnit 安装脚本 - HarmonyOS/OpenHarmony
# 用法: sh install.sh [版本号]

VERSION="${1:-2.1-3}"
PREFIX="${HOME}/usr/local"
TARBALL="cunit-${VERSION}-ohos-aarch64.tar.gz"

echo "安装 CUnit ${VERSION} 到 ${PREFIX}"

# 创建目录
mkdir -p "${PREFIX}/lib" "${PREFIX}/include/CUnit"

# 解压 tarball
if [ -f "packaging/${TARBALL}" ]; then
    tar -xzf "packaging/${TARBALL}" -C "${PREFIX}"
    echo "✅ CUnit ${VERSION} 安装成功"
    echo ""
    echo "使用方法:"
    echo "  编译: clang -I${PREFIX}/include/CUnit -L${PREFIX}/lib -lcunit your_test.c"
    echo ""
else
    echo "❌ 找不到打包文件: packaging/${TARBALL}"
    exit 1
fi