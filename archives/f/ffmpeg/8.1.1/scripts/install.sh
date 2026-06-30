#!/bin/bash
# FFmpeg 8.1.1 安装脚本
# 用于鸿蒙系统的预编译包安装

set -e

VERSION="8.1.1"
PACKAGE_NAME="ffmpeg-${VERSION}-ohos-aarch64"
INSTALL_PREFIX="${HOME}/usr/local"

# 默认安装路径
if [ -z "$PREFIX" ]; then
    PREFIX="${INSTALL_PREFIX}"
fi

# 创建目录
mkdir -p "${PREFIX}/bin"

# 解压并安装
echo "正在安装 FFmpeg ${VERSION} 到 ${PREFIX}..."

# 检查包文件是否存在
if [ ! -f "${PACKAGE_NAME}.tar.gz" ]; then
    echo "错误: 找不到包文件 ${PACKAGE_NAME}.tar.gz"
    exit 1
fi

# 解压
tar -xzf "${PACKAGE_NAME}.tar.gz"

# 安装二进制文件
if [ -d "bin" ]; then
    cp -a bin/* "${PREFIX}/bin/"
else
    # 如果没有 bin 目录，直接复制文件
    cp -a ffmpeg ffprobe "${PREFIX}/bin/"
fi

# 清理解压文件
rm -rf bin ffmpeg ffprobe

# 设置权限
chmod 755 "${PREFIX}/bin/ffmpeg"
chmod 755 "${PREFIX}/bin/ffprobe"

# 验证安装
echo ""
echo "安装完成！"
echo ""
echo "验证安装:"
"${PREFIX}/bin/ffmpeg" -version | head -1
"${PREFIX}/bin/ffprobe" -version | head -1
echo ""
echo "使用方法:"
echo "  ffmpeg -i input.mp4 -c:v libx264 output.mp4   # 视频转码"
echo "  ffprobe input.mp4                              # 查看媒体信息"
echo ""
echo "注意: 二进制文件已进行 ELF 签名，可以直接运行"