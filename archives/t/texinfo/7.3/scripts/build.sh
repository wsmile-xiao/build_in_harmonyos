#!/bin/sh
# texinfo 7.3 构建脚本
# 用于在 HarmonyOS 上编译 texinfo

set -e

# 配置变量
PREFIX="/storage/Users/currentUser/usr/local"
BUILD_DIR="/storage/Users/currentUser/codeyilihr/0330/build_in_harmonyos/texinfo-7.3"
SOURCE_TARBALL="${BUILD_DIR}/../texinfo-7.3.tar.xz"

echo "=== texinfo 7.3 构建脚本 ==="
echo "构建目录: ${BUILD_DIR}"
echo "安装前缀: ${PREFIX}"
echo ""

# 检查源码包
if [ ! -f "${SOURCE_TARBALL}" ]; then
    echo "错误: 源码包不存在: ${SOURCE_TARBALL}"
    exit 1
fi

echo "✅ 源码包存在"

# 检查工作目录
if [ ! -d "${BUILD_DIR}" ]; then
    echo "错误: 构建目录不存在: ${BUILD_DIR}"
    exit 1
fi

echo "✅ 构建目录存在"

# 进入构建目录
cd "${BUILD_DIR}"

# 执行 configure
echo ""
echo "=== 配置阶段 ==="
echo "执行 configure..."
./configure \
  --prefix="${PREFIX}" \
  --disable-nls \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  CC=clang \
  CFLAGS="-I${PREFIX}/include" \
  LDFLAGS="-L${PREFIX}/lib"

if [ $? -ne 0 ]; then
    echo "错误: configure 失败"
    exit 1
fi

echo "✅ configure 成功"

# 执行 make
echo ""
echo "=== 编译阶段 ==="
echo "执行 make..."
make

if [ $? -ne 0 ]; then
    echo "错误: make 失败"
    exit 1
fi

echo "✅ 编译成功"

# 执行 make install
echo ""
echo "=== 安装阶段 ==="
echo "执行 make install..."
make install

if [ $? -ne 0 ]; then
    echo "错误: make install 失败"
    exit 1
fi

echo "✅ 安装成功"

# 验证安装
echo ""
echo "=== 验证阶段 ==="
if [ -x "${BUILD_DIR}/install-info/ginstall-info" ]; then
    echo "✅ install-info 已安装: ${BUILD_DIR}/install-info/ginstall-info"
    ${BUILD_DIR}/install-info/ginstall-info --version | head -1
else
    echo "错误: install-info 未正确安装"
    exit 1
fi

echo ""
echo "=== 构建完成 ==="
echo "texinfo 7.3 已成功编译并安装到 ${PREFIX}"
