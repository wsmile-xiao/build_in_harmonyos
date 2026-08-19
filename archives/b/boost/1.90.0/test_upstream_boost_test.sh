#!/system/bin/sh
# test_upstream_boost_test.sh — 官方上游 Boost.Test 测试 harness（boost 1.90.0）
#
# 背景（R04 根因）：
#   上游 Boost.Test 的 libs/test/build/CMakeLists.txt 对非 MSVC 强制追加 -std=c++11
#   （check_cxx_compiler_flag(-std=c++11 HAS_CXX11_FLAG) 命中后 set(CMAKE_CXX_FLAGS ... -std=c++11)），
#   而 Boost 1.90.0 的 boost/multiprecision + boost/math/tools/type_traits.hpp 使用
#   C++14/17 才有的 std::is_null_pointer / std::is_final / std::*_t 别名，
#   导致 72 个上游用例（含 fp-multiprecision 系列）在 C++11 下编译失败、可执行文件未生成。
#
# 最小修复（不修改任何上游源码，仅修正测试构建的编译标准）：
#   1. 预置 HAS_CXX11_FLAG=FALSE / HAS_CXX0X_FLAG=FALSE，使上游 CMakeLists 跳过
#      "-std=c++11" 追加（check_cxx_compiler_flag 在变量已定义时直接复用缓存值）。
#   2. 显式 -DCMAKE_CXX_FLAGS="-std=c++17"，保证 Boost 1.90.0 所需最低标准。
#   本 harness 不改变 boost 配方（包/导出/消费者），仅驱动官方上游自测。
#
# 用法：
#   sh test_upstream_boost_test.sh <verified_source_root> [build_dir]
#   例：sh test_upstream_boost_test.sh /storage/Users/currentUser/.conan2/p/boost1e883b6e252a4/s

set -u

SRC="${1:?usage: test_upstream_boost_test.sh <verified_source_root> [build_dir]}"
CFG="${2:-r04-cfg}"
BASE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SRC/boost/version.hpp" ]; then
    echo "ERROR: verified source root invalid: $SRC" >&2
    exit 2
fi
if [ ! -d "$SRC/libs/test/build" ]; then
    echo "ERROR: libs/test/build missing in $SRC" >&2
    exit 2
fi

BT_DIR="$SRC/libs/test/build"
cd "$BT_DIR"
rm -rf "$CFG"
mkdir -p "$CFG"
cd "$CFG"

export PATH="/data/service/hnp/bin:$PATH"

CONF_LOG="$BASE/reports/upstream-btest-configure.log"
BUILD_LOG="$BASE/reports/upstream-btest-build.log"
CTEST_LOG="$BASE/reports/upstream-btest-ctest.log"

echo "=== configure official Boost.Test upstream build (C++17, OHOS clang) ==="
cmake .. \
    -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
    -DCMAKE_AR=/data/service/hnp/bin/llvm-ar \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITHOUT_TESTS=OFF \
    -DBUILD_TESTING=ON \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DHAS_CXX11_FLAG=FALSE \
    -DHAS_CXX0X_FLAG=FALSE \
    -DCMAKE_CXX_FLAGS="-std=c++17" \
    > "$CONF_LOG" 2>&1
CONFIGURE_EXIT=$?
echo "CONFIGURE_EXIT=$CONFIGURE_EXIT"
tail -5 "$CONF_LOG"

if [ "$CONFIGURE_EXIT" -ne 0 ]; then
    echo "HARNESS_ABORT: configure failed"
    exit "$CONFIGURE_EXIT"
fi

echo "=== build official Boost.Test upstream suite ==="
cmake --build . -j8 > "$BUILD_LOG" 2>&1
BUILD_EXIT=$?
echo "BUILD_EXIT=$BUILD_EXIT"
tail -8 "$BUILD_LOG"

echo "=== run ctest ==="
ctest -j8 > "$CTEST_LOG" 2>&1
CTEST_EXIT=$?
echo "CTEST_EXIT=$CTEST_EXIT"
grep -E "tests passed" "$CTEST_LOG"

echo "=== harness done: build_exit=$BUILD_EXIT ctest_exit=$CTEST_EXIT ==="
exit 0
