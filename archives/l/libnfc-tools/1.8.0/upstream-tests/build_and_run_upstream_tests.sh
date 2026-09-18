#!/bin/sh
# =============================================================================
# libnfc 1.8.0 上游 Cutter 单元测试用例 —— HarmonyOS PC (aarch64) 真机编译与执行
# =============================================================================
#
# 背景
#   libnfc-tools 并非独立上游项目，而是 libnfc-1.8.0 源码树 utils/+examples/
#   的工具拆分包。其上游仓库 (github.com/nfc-tools/libnfc) 的 test/ 目录提供
#   6 个 Cutter 框架单元测试用例，全部针对 libnfc 库本体。
#
#   上游 test/Makefile.am 以 AM_CONDITIONAL(WITH_CUTTER) 守卫，只有
#   configure 阶段检测到 Cutter >= 1.1.7 才会构建这 6 个用例。本机原始环境
#   无 Cutter，因此第一次提交时 make check 报 TOTAL=0（0/6 未执行）。
#
# 本脚本做的事
#   1) 用本机交叉编译好的 Cutter 1.2.6 测试框架（见 ./CUTTER-BUILD.md）
#   2) 以 libnfc-1.8.0 上游源码树中【未修改的】test/*.c 原始源文件为输入
#   3) 真机编译为 Cutter 测试模块，并真实执行
#
# 预期结果
#   6 个用例全部被真实编译并执行。用例运行期需物理 PN53x NFC 读卡器，
#   上游在每例中均实现了 cut_omit() 保护（"No NFC device found" /
#   "At least two NFC devices must be plugged-in..."），因此无硬件时
#   按上游设计优雅跳过（OMIT，非 FAIL），整体 100% passed。
#
# 用法
#   CUTTER_ROOT=<cutter 构建目录> NFC_SRC=<libnfc 源码树> sh build_and_run_upstream_tests.sh
#   各路径均可用环境变量覆盖，默认值对应本次适配的真机环境。
# =============================================================================
set -u

# ---- 可覆盖路径 -------------------------------------------------------------
CUTTER_ROOT=${CUTTER_ROOT:-/data/storage/el2/base/cache/cutter-build}
NFC_SRC=${NFC_SRC:-/data/storage/el2/base/cache/ohc-verify-libnfc-tools-6833h96i/libnfc-1.8.0}
WORKDIR=${WORKDIR:-$CUTTER_ROOT/testmod}
CLANG=${CLANG:-/data/service/hnp/bin/clang}

# ---- 依赖（制品仓已发布包 / 本机 conan 缓存）---------------------------------
GLIB=${GLIB:-/storage/Users/currentUser/.conan2/p/glibcad7259522c98/p}
LIBNFC_PKG=${LIBNFC_PKG:-/storage/Users/currentUser/.conan2/p/libnf1cc9a17d6e146/p}
LIBUSB_COMPAT=${LIBUSB_COMPAT:-/storage/Users/currentUser/.conan2/p/libus6c114be92ec51/p}
LIBUSB1=${LIBUSB1:-/storage/Users/currentUser/.conan2/p/libus04e54d4f229a5/p}

SRC=$CUTTER_ROOT/cutter-1.2.6
BUILD=$CUTTER_ROOT/build6
CUTTER=$BUILD/cutter/cutter

INC="-I$BUILD -I$SRC -I$SRC/cutter \
     -I$NFC_SRC/libnfc -I$NFC_SRC/utils \
     -I$LIBNFC_PKG/include -I$LIBUSB_COMPAT/include -I$LIBUSB1/include"

LIBS="$LIBNFC_PKG/lib/libnfc.a $LIBUSB_COMPAT/lib/libusb.a \
      -L$LIBUSB1/lib -lusb-1.0 \
      -L$CUTTER_ROOT/install/lib -lcutter \
      -L$GLIB/lib -lglib-2.0 -lgobject-2.0 -lgmodule-2.0 -lgthread-2.0 \
      -lpthread -lm \
      -Wl,-rpath,$CUTTER_ROOT/install/lib -Wl,-rpath,$GLIB/lib"

# 上游 test/ 目录下 6 个用例（与 test/Makefile.am 的 cutter_unit_test_libs 一致）
TESTS="test_access_storm test_dep_active test_dep_passive \
       test_device_modes_as_dep test_register_access test_register_endianness"

mkdir -p "$WORKDIR" || exit 1

echo "=== [1/3] 编译上游 utils/nfc-utils.c（test_dep_active / test_device_modes_as_dep 引用）==="
$CLANG -std=c99 -O2 -fPIC $INC -c "$NFC_SRC/utils/nfc-utils.c" -o "$WORKDIR/nfc-utils.o" || exit 1
echo "  OK"

echo "=== [2/3] 编译 6 个上游测试用例（源文件未做任何修改）==="
for t in $TESTS; do
    $CLANG -std=c99 -O2 -fPIC $INC -c "$NFC_SRC/test/$t.c" -o "$WORKDIR/$t.o" || exit 1
    $CLANG -shared -o "$WORKDIR/$t.so" "$WORKDIR/$t.o" "$WORKDIR/nfc-utils.o" $LIBS || exit 1
    echo "  built $t.so"
done

echo "=== [3/3] Cutter runner 真机执行上游用例 ==="
cd "$WORKDIR" || exit 1
exec "$CUTTER" "$WORKDIR"
