#!/bin/bash
# run_on_device.sh - 在鸿蒙真机上运行 zlib-ng 2.3.3 上游 GoogleTest 测试套件
#
# 本脚本做三件事：
#   1. 用 OHOS NDK 交叉编译 zlib-ng 2.3.3 + GoogleTest（产出 aarch64-linux-ohos 静态二进制）
#   2. 用 hdc 把二进制推到真机 /data/local/tmp/
#   3. hdc shell 在真机执行，抓取真实通过率日志，拉回本地
#
# === 使用前提 ===
#   A. 已安装 DevEco Studio（自带 hdc + OHOS SDK NDK），或单独装了 commandline-tools
#   B. 鸿蒙真机已开启「开发者模式 + USB 调试」，用 USB 连到电脑
#   C. 终端能执行 hdc（Windows 用 hdc.exe，Mac/Linux 用 hdc）
#
# === 使用方法 ===
#   Linux/Mac:
#     chmod +x run_on_device.sh
#     ./run_on_device.sh
#   Windows (Git Bash 或 WSL):
#     bash run_on_device.sh
#
# === 首次运行若提示找不到 hdc / NDK，请用环境变量指定路径 ===
#   export HDC=/path/to/hdc              # hdc 可执行文件路径
#   export OHOS_NDK=/path/to/sdk/native  # OHOS SDK native 目录
#   ./run_on_device.sh
#
# DevEco Studio 默认路径（供参考）：
#   Windows HDC : C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe
#   Windows NDK : C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native
#   Mac HDC     : ~/Library/Huawei/Sdk/default/openharmony/toolchains/hdc
#   Mac NDK     : ~/Library/Huawei/Sdk/default/openharmony/native
#   Linux HDC   : ~/ohos-sdk/default/openharmony/toolchains/hdc
#   Linux NDK   : ~/ohos-sdk/default/openharmony/native

set -euo pipefail

ZLIB_NG_VERSION="2.3.3"
WORK_DIR="$(mktemp -d /tmp/zlib-ng-ohos-XXXXXX)"
SRC_DIR="$WORK_DIR/zlib-ng-${ZLIB_NG_VERSION}"
BUILD_DIR="$SRC_DIR/build-ohos"
REMOTE_DIR="/data/local/tmp/zlib_ng_test"

# ---- 0. 检测 hdc ----
HDC="${HDC:-}"
if [ -z "$HDC" ]; then
  HDC=$(command -v hdc 2>/dev/null || command -v hdc.exe 2>/dev/null || true)
fi
if [ -z "$HDC" ]; then
  # 尝试 DevEco Studio 默认路径
  for p in \
    "/c/Program Files/Huawei/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe" \
    "$HOME/Library/Huawei/Sdk/default/openharmony/toolchains/hdc" \
    "$HOME/ohos-sdk/default/openharmony/toolchains/hdc"; do
    if [ -x "$p" ] || [ -f "$p" ]; then HDC="$p"; break; fi
  done
fi
if [ -z "$HDC" ]; then
  echo "[ERROR] 找不到 hdc。请用 export HDC=/path/to/hdc 指定，或把 hdc 加入 PATH。"
  exit 1
fi
echo "[0/6] hdc = $HDC"

# ---- 检测真机连接 ----
echo "[0/6] 检测真机连接..."
TARGETS=$("$HDC" list targets 2>&1)
if echo "$TARGETS" | grep -qiE "empty|no device|\[Empty\]"; then
  echo "[ERROR] 没有检测到真机。请确认："
  echo "  1. 真机已用 USB 连到电脑"
  echo "  2. 真机已开启 开发者模式 + USB 调试"
  echo "  3. 真机弹窗点了「允许调试」"
  echo "  hdc list targets 输出: $TARGETS"
  exit 1
fi
echo "  已连接设备: $TARGETS"

# ---- 检测 OHOS NDK ----
OHOS_NDK="${OHOS_NDK:-}"
if [ -z "$OHOS_NDK" ]; then
  for p in \
    "/c/Program Files/Huawei/DevEco Studio/sdk/default/openharmony/native" \
    "$HOME/Library/Huawei/Sdk/default/openharmony/native" \
    "$HOME/ohos-sdk/default/openharmony/native"; do
    if [ -f "$p/build/cmake/ohos.toolchain.cmake" ]; then OHOS_NDK="$p"; break; fi
  done
fi
if [ -z "$OHOS_NDK" ] || [ ! -f "$OHOS_NDK/build/cmake/ohos.toolchain.cmake" ]; then
  echo "[ERROR] 找不到 OHOS NDK。请用 export OHOS_NDK=/path/to/sdk/native 指定。"
  echo "  NDK 目录下应包含 build/cmake/ohos.toolchain.cmake"
  exit 1
fi
CMAKE_BIN="$OHOS_NDK/build-tools/cmake/bin/cmake"
NINJA_BIN="$OHOS_NDK/build-tools/cmake/bin/ninja"
TOOLCHAIN_FILE="$OHOS_NDK/build/cmake/ohos.toolchain.cmake"
echo "[0/6] OHOS_NDK = $OHOS_NDK"

# ---- 1. 下载源码 ----
echo "[1/6] 下载 zlib-ng ${ZLIB_NG_VERSION} 源码..."
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
TARBALL="$WORK_DIR/zlib-ng-${ZLIB_NG_VERSION}.tar.gz"
EXPECTED_SHA256="f9c65aa9c852eb8255b636fd9f07ce1c406f061ec19a2e7d508b318ca0c907d1"
curl -sL "https://github.com/zlib-ng/zlib-ng/archive/refs/tags/${ZLIB_NG_VERSION}.tar.gz" -o "$TARBALL"
ACTUAL_SHA256="$(sha256sum "$TARBALL" | awk '{print $1}')"
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  echo "[ERROR] sha256 校验失败：期望 $EXPECTED_SHA256，实际 $ACTUAL_SHA256"
  exit 1
fi
tar -xf "$TARBALL"
cd "$SRC_DIR"

# ---- 2. 配置交叉编译 ----
echo "[2/6] 配置 OHOS aarch64 交叉编译 (WITH_GTEST=ON, 静态链接)..."
"$CMAKE_BIN" -S . -B "$BUILD_DIR" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE" \
  -DOHOS_ARCH=arm64-v8a -DOHOS_PLATFORM=OHOS \
  -DOHOS_SDK_NATIVE="$OHOS_NDK" -DOHOS_STL=c++_static \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON -DWITH_GTEST=ON -DWITH_GZFILEOP=ON \
  -DCMAKE_MAKE_PROGRAM="$NINJA_BIN" \
  -DCMAKE_C_FLAGS="-static -fPIC" -DCMAKE_CXX_FLAGS="-static -fPIC" -DCMAKE_EXE_LINKER_FLAGS="-static"

# ---- 3. 编译 ----
echo "[3/6] 编译 gtest_zlib / example / infcover..."
"$CMAKE_BIN" --build "$BUILD_DIR" --target gtest_zlib example infcover -j"$(nproc 2>/dev/null || echo 4)"

# ---- 4. 推送到真机 ----
echo "[4/6] 推送二进制到真机 $REMOTE_DIR ..."
"$HDC" shell "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR"
"$HDC" file send "$BUILD_DIR/gtest_zlib" "$REMOTE_DIR/gtest_zlib"
"$HDC" file send "$BUILD_DIR/example"    "$REMOTE_DIR/example"
"$HDC" file send "$BUILD_DIR/infcover"   "$REMOTE_DIR/infcover"
"$HDC" shell "chmod +x $REMOTE_DIR/gtest_zlib $REMOTE_DIR/example $REMOTE_DIR/infcover"

# ---- 5. 真机执行 ----
echo "[5/6] 在真机执行测试..."
echo "==================== gtest_zlib ===================="
"$HDC" shell "cd $REMOTE_DIR && ./gtest_zlib 2>&1" | tee "$WORK_DIR/gtest_output.txt"
echo ""
echo "==================== example ===================="
"$HDC" shell "cd $REMOTE_DIR && ./example; echo example_exit=\$?"
echo "==================== infcover ===================="
"$HDC" shell "cd $REMOTE_DIR && ./infcover; echo infcover_exit=\$?"

# ---- 6. 拉取日志 ----
LOCAL_LOG="$(pwd)/zlib_ng_ohos_gtest_log.txt"
cp "$WORK_DIR/gtest_output.txt" "$LOCAL_LOG"
echo ""
echo "[6/6] 完成！日志已保存到: $LOCAL_LOG"
echo ""
echo "==================== 通过率汇总 ===================="
grep -E "Running|tests ran|PASSED|FAILED" "$LOCAL_LOG" | grep -vE "^\[  (SKIPPED|PASSED|FAILED)\]" | tail -5 || true
echo ""
echo "请把 $LOCAL_LOG 的内容贴到 PR 评论作为真机测试证据。"
