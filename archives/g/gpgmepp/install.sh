#!/bin/sh
# gpgmepp OpenHarmony 安装脚本
# 用法: sh install.sh [版本]
# 示例: sh install.sh 1.23.2

PREFIX="${HOME}/usr/local"
VERSION="${1:-1.23.2}"
ARCHIVE="gpgmepp-${VERSION}-ohos-aarch64.tar.gz"

echo "安装 gpgmepp ${VERSION} 到 $PREFIX..."

if [ ! -f "$ARCHIVE" ]; then
    # 尝试从当前目录或 packaging 目录查找
    if [ -f "packaging/$ARCHIVE" ]; then
        ARCHIVE="packaging/$ARCHIVE"
    elif [ -f "${VERSION}/packaging/$ARCHIVE" ]; then
        ARCHIVE="${VERSION}/packaging/$ARCHIVE"
    else
        echo "错误：找不到预编译包 $ARCHIVE"
        echo "请确保文件存在于当前目录或 packaging/ 目录"
        exit 1
    fi
fi

mkdir -p "$PREFIX/bin" "$PREFIX/lib" "$PREFIX/include" "$PREFIX/share"

tar xzf "$ARCHIVE" -C "$PREFIX" --strip-components=0

echo "gpgmepp ${VERSION} 安装完成！"
echo ""
echo "安装内容："
echo "  库文件: libgpgme.so, libgpgmepp.so"
echo "  头文件: gpgme.h, gpgme++/"
echo "  工具: gpgme-tool, gpgme-json"
echo ""
echo "注意：运行时需要依赖 libgpg-error 和 libassuan"
echo "请确保已安装这些依赖库"