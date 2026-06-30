#!/bin/sh
# bowtie2 在 HarmonyOS/OpenHarmony (aarch64) 上的构建脚本
# bowtie2 使用纯 Makefile，非 autotools/configure
# simde submodule 需单独填充

set -e

# 步骤1: 填充 third_party/simde submodule（Release tarball 不含内容）
if [ ! -f third_party/simde/x86/sse2.h ]; then
    echo "填充 simde submodule..."
    SIMDE_URL="https://github.com/simd-everywhere/simde-no-tests/archive/refs/heads/master.tar.gz"
    TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}"
    curl -fsSL -k "$SIMDE_URL" -o "$TMPDIR/simde-no-tests.tar.gz"
    cd "$TMPDIR" && tar xzf simde-no-tests.tar.gz
    rm -rf third_party/simde
    cp -a "$TMPDIR/simde-no-tests-master" third_party/simde
    rm -rf "$TMPDIR/simde-no-tests-master" "$TMPDIR/simde-no-tests.tar.gz"
    cd -
fi

# 步骤2: 编译
make PREFIX="${DEFAULT_PREFIX:-/storage/Users/currentUser/usr/local}" \
     CXX="${CXX:-clang++}" \
     CC="${CC:-clang}" \
     -j2

# 步骤3: 安装（DESTDIR 模式）
make install \
     PREFIX="${DEFAULT_PREFIX:-/storage/Users/currentUser/usr/local}" \
     DESTDIR="${TEST_PREFIX:-/storage/Users/currentUser/tmp/test-install-bowtie2-2.5.5}"

echo "构建完成"