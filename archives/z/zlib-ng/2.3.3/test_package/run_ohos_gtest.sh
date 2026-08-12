#!/bin/bash
# run_ohos_gtest.sh - 在鸿蒙真机（或 OHOS 真机环境）上编译并运行 zlib-ng 2.3.3 上游 GoogleTest 测试套件
#
# 用途：满足赛事规则 5「上游测试通过率」要求，提供真实通过率数据。
#
# 前置条件（鸿蒙真机已安装 DevBox / HiShell 可用）：
#   - clang / clang++（OHOS NDK 自带，目标 aarch64-linux-ohos）
#   - cmake + ninja
#   - git（用于 FetchContent 拉取 GoogleTest 1.12.1）
#   - 网络可访问 github.com（拉取 GoogleTest 源码）
#
# 若真机无网络拉取 GoogleTest，可在有网络主机上预先构建 gtest_zlib
# 可执行文件（aarch64-linux-ohos 静态链接），再 hdc 推送到真机运行。
#
# 使用方法：
#   chmod +x run_ohos_gtest.sh
#   ./run_ohos_gtest.sh
#
# 预期输出（实测数据）：
#   [==========] Running 1141 tests from 18 test suites.
#   [  PASSED  ] 468 tests.
#   [  SKIPPED ] 673 tests   (ARM 平台不支持的 x86/AVX/vpclmulqdq 等特性)
#   [  FAILED  ] 0 tests
#   example    : PASSED (exit 0)
#   infcover   : PASSED (exit 0)

set -euo pipefail

ZLIB_NG_VERSION="2.3.3"
SRC_DIR="zlib-ng-${ZLIB_NG_VERSION}"
BUILD_DIR="build-ohos-gtest"
ARCHIVE_URL="https://github.com/zlib-ng/zlib-ng/archive/refs/tags/${ZLIB_NG_VERSION}.tar.gz"
EXPECTED_SHA256="f9c65aa9c852eb8255b636fd9f07ce1c406f061ec19a2e7d508b318ca0c907d1"

# ---- 1. 准备源码 ----
if [ ! -d "$SRC_DIR" ]; then
  echo "[1/5] 下载 zlib-ng ${ZLIB_NG_VERSION} 源码..."
  TARBALL="$(mktemp)"
  curl -sL "$ARCHIVE_URL" -o "$TARBALL"
  ACTUAL_SHA256="$(sha256sum "$TARBALL" | awk '{print $1}')"
  if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "[ERROR] sha256 校验失败：期望 $EXPECTED_SHA256，实际 $ACTUAL_SHA256"
    rm -f "$TARBALL"
    exit 1
  fi
  tar -xf "$TARBALL"
  rm -f "$TARBALL"
fi
cd "$SRC_DIR"

# ---- 2. 检测 OHOS 工具链 ----
# 优先使用 OHOS NDK 自带 cmake/ninja，回退到 PATH 中的
OHOS_NDK="${OHOS_NDK:-/data/local/tmp/ohos-sdk/linux/native}"
if [ -x "$OHOS_NDK/build-tools/cmake/bin/cmake" ]; then
  CMAKE_BIN="$OHOS_NDK/build-tools/cmake/bin/cmake"
  NINJA_BIN="$OHOS_NDK/build-tools/cmake/bin/ninja"
  TOOLCHAIN_FILE="$OHOS_NDK/build/cmake/ohos.toolchain.cmake"
else
  CMAKE_BIN="$(command -v cmake)"
  NINJA_BIN="$(command -v ninja)"
  TOOLCHAIN_FILE="${OHOS_TOOLCHAIN_FILE:-$OHOS_NDK/build/cmake/ohos.toolchain.cmake}"
fi
echo "[2/5] CMAKE=$CMAKE_BIN  NINJA=$NINJA_BIN  TOOLCHAIN=$TOOLCHAIN_FILE"

# ---- 3. 配置（OHOS aarch64 + WITH_GTEST=ON + 静态链接，规避 .so 签名）----
echo "[3/5] 配置 OHOS aarch64 交叉编译 (WITH_GTEST=ON, 静态链接)..."
rm -rf "$BUILD_DIR"
"$CMAKE_BIN" -S . -B "$BUILD_DIR" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE" \
  -DOHOS_ARCH=arm64-v8a \
  -DOHOS_PLATFORM=OHOS \
  -DOHOS_SDK_NATIVE="$OHOS_NDK" \
  -DOHOS_STL=c++_static \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=ON \
  -DWITH_GTEST=ON \
  -DWITH_GZFILEOP=ON \
  -DCMAKE_MAKE_PROGRAM="$NINJA_BIN" \
  -DCMAKE_C_FLAGS="-static -fPIC" \
  -DCMAKE_CXX_FLAGS="-static -fPIC" \
  -DCMAKE_EXE_LINKER_FLAGS="-static"

# ---- 4. 编译 gtest_zlib / example / infcover ----
echo "[4/5] 编译测试目标 (gtest_zlib, example, infcover)..."
"$CMAKE_BIN" --build "$BUILD_DIR" --target gtest_zlib example infcover -j"$(nproc)"

# ---- 5. 运行测试 ----
echo "[5/5] 运行上游测试套件..."
cd "$BUILD_DIR"

echo "==================== gtest_zlib ===================="
set +e
./gtest_zlib 2>&1 | tail -5
GTEST_RC=${PIPESTATUS[0]}
set -e
echo "gtest_zlib exit=$GTEST_RC"

OVERALL_RC=0

echo "==================== example ===================="
if ./example >/dev/null 2>&1; then echo "example: PASSED (exit 0)"; else echo "example: FAILED"; OVERALL_RC=1; fi
echo "==================== infcover ===================="
if ./infcover >/dev/null 2>&1; then echo "infcover: PASSED (exit 0)"; else echo "infcover: FAILED"; OVERALL_RC=1; fi

echo ""
echo "==================== 汇总 ===================="
set +e
./gtest_zlib 2>&1 | grep -E "Running|tests ran|PASSED|FAILED" | \
  grep -vE "^\[  (SKIPPED|PASSED|FAILED)\]" | tail -5
set -e

# 任一测试失败则以非零退出码结束
if [ "$GTEST_RC" -ne 0 ]; then OVERALL_RC="$GTEST_RC"; fi
exit "$OVERALL_RC"
