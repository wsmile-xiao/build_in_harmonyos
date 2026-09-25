#!/bin/bash
# upstream_tests.sh — 在刚刚构建完成的 autotools 树之上，真实编译并运行
# siril 1.2.3 上游单元测试（src/tests/），输出 HMBS_UPSTREAM_TEST_RESULT 机器证据。
#
# 上游测试套件依赖 Criterion（criterion/criterion.h），且仅以 meson 构建；
# 本配方是 autotools 构建，故此处按上游 build.sh 的方式手工编译测试程序：
#   - 无 Criterion 路径的测试（compare_fits / measure_sorting）直接用 main；
#   - 其余测试编译时加 -DWITH_MAIN（文件内置的非 Criterion 主入口）；
#   - imoper/soper/photometry/rejection/sorting 使用 Criterion 断言，
#     链接仓库内 Criterion 静态库（来自 tool_requires criterion/2.4.3）。
# 链接时通过 -Wl,--unresolved-symbols=ignore-all 忽略未引用符号（与上游
# meson 的 link_args 一致）；核心对象打成 libsiril_core.a 以惰性拉取。
#
# 环境变量（由 conanfile.py 的 build() 注入）：
#   SIRIL_SOURCE   源码根目录（含 src/tests/）
#   SIRIL_BUILD    VPATH 构建根目录（含 config.h 与 src/ 下的 .o）
#   CRITERION_INCLUDE / CRITERION_LIB   Criterion 包的头文件/库目录
#   SIRIL_TESTS_OUT  结果输出目录（默认 $SIRIL_BUILD/upstream-tests）
#   CC / CXX / CPPFLAGS / CFLAGS / LDFLAGS / LIBS  来自 conan build 环境
set -u

SRC="${SIRIL_SOURCE:?SIRIL_SOURCE not set}"
BD="${SIRIL_BUILD:?SIRIL_BUILD not set}"
CRI="${CRITERION_INCLUDE:?CRITERION_INCLUDE not set}"
CRL="${CRITERION_LIB:?CRITERION_LIB not set}"
OUT="${SIRIL_TESTS_OUT:-$BD/upstream-tests}"

# 与本地验证一致的构建/运行环境（含全部依赖的 LD_LIBRARY_PATH）。
GEN="$BD/conan"
[ -f "$GEN/conanbuild.sh" ] && . "$GEN/conanbuild.sh" >/dev/null 2>&1
[ -f "$GEN/conanrun.sh" ] && . "$GEN/conanrun.sh" >/dev/null 2>&1

# 链接阶段用的 LD_LIBRARY_PATH：剥离 conan 注入的目标(aarch64)库目录。
# 上游测试链接由 host 链接器(lld)完成，而 lld 自身动态依赖 libxml2.so.16
# 等 host 库（CI worker OHOS SDK 26 的 lld 即如此）；若 LD_LIBRARY_PATH
# 抢先把错误架构的 conan libxml2 加载给 lld，会触发 "Error relocating ...
# symbol not found" 导致链接崩溃（CI 构建 #49400 全部 LINK FAILED）。
# 链接仅需 -L 显式路径，无需 LD_LIBRARY_PATH 指向目标库；运行阶段仍用完整路径。
FULL_LD="${LD_LIBRARY_PATH:-}"
CONAN_HOME_DIR="${CONAN_HOME:-$HOME/.conan2}"
LINK_LD=""
IFS=':' read -ra _ld_parts <<< "$FULL_LD"
for _p in "${_ld_parts[@]}"; do
    case "$_p" in
        "$CONAN_HOME_DIR/p/"*|"$HOME/.conan2/p/"*|*/conan2/p/*) ;;  # 跳过 conan 包目录
        *) LINK_LD="${LINK_LD:+$LINK_LD:}$_p" ;;
    esac
done

mkdir -p "$OUT/tmp"
cd "$OUT" || exit 1

CC="${CC:-clang}"
CXX="${CXX:-clang++}"
OBJDIR="$BD/src"

CFLAGS_ALL="-DHAVE_CONFIG_H -D_FILE_OFFSET_BITS=64 -I$CRI -I$OBJDIR -I$BD -I$SRC -I$SRC/src -I$SRC/src/tests $CPPFLAGS $CFLAGS"
CRITERION_LIBS="$CRL/libcriterion.a $CRL/libffi.a -L$CRL/../usr/lib -lnanomsg -lprotobuf_nanopb_static"

# 核心对象静态库（排除 main.o/main-cli.o——它们各自有 main() 且定义 com/gui/gfit）。
AR_BIN="$(command -v llvm-ar || command -v ar || echo llvm-ar)"
"$AR_BIN" rcs libsiril_core.a \
    $(find "$OBJDIR" -name "*.o" ! -name "main.o" ! -name "main-cli.o") \
    || { echo "[tests] libsiril_core.a 创建失败"; exit 1; }
CORE="$OUT/libsiril_core.a"
KPLOT="$BD/subprojects/kplot/libkplot.a"
HTMESH="$BD/subprojects/htmesh/build/libhtmesh.a"
[ -f "$KPLOT" ] || KPLOT=""
[ -f "$HTMESH" ] || HTMESH=""
LDLIBS="-L$CRL $LDFLAGS -fopenmp $CORE $KPLOT $HTMESH $LIBS $CRITERION_LIBS"

# 应用级全局变量（com/gui/gfit 只定义在 main.c/main-cli.c 中；WITH_MAIN 测试
# 自身不定义它们，而上游 build.sh 靠 dummy.c 提供桩，这里提供真定义即可）。
cat > globals.c <<'EOF'
#include "core/siril.h"
cominfo com;
guiinfo gui;
fits gfit;
EOF
$CC $CFLAGS_ALL -c -o globals.o globals.c || exit 1

# ser_test 硬编码 /tmp 临时文件路径，而本设备 /tmp 只读；重定向到可写目录。
sed "s|/tmp/test_tmp|$OUT/tmp/test_tmp|g" "$SRC/src/tests/ser_test.c" > ser_test_src.c

# compare_fits 需要两个 FITS 文件实参；生成两份字节相同的 8x8 最小 FITS。
make_fits() {
    local f="$1"
    {
        printf '%-80s' "SIMPLE  =                    T / file does conform to FITS standard"
        printf '%-80s' "BITPIX  =                    8 / 8-bit unsigned integer data"
        printf '%-80s' "NAXIS   =                    2 / number of data axes"
        printf '%-80s' "NAXIS1  =                    8 / length of data axis 1"
        printf '%-80s' "NAXIS2  =                    8 / length of data axis 2"
        printf '%-80s' "END"
        head -c 2800 /dev/zero
        head -c 64 /dev/zero
        head -c 2816 /dev/zero
    } > "$f"
}
make_fits a.fit
make_fits b.fit

pass=0; fail=0; failed_list=""; ran=0

run_one() {
    local name="$1"; shift
    local compile_cmd="$1"; shift
    local link_cmd="$1"; shift
    local run_cmd="${1:-./$name}"
    echo "===== BUILD $name ====="
    if ! eval "$compile_cmd" ; then
        echo "[$name] COMPILE FAILED"
        fail=$((fail+1)); failed_list="$failed_list $name(compile)"
        return
    fi
    if ! LD_LIBRARY_PATH="$LINK_LD" eval "$link_cmd" ; then
        echo "[$name] LINK FAILED"
        fail=$((fail+1)); failed_list="$failed_list $name(link)"
        return
    fi
    echo "===== RUN $name ====="
    ran=$((ran+1))
    local rc=0
    timeout 900 bash -c "$run_cmd" > "$name.out" 2>&1; rc=$?
    if [ $rc -eq 0 ]; then
        echo "[$name] PASS (rc=0)"
        pass=$((pass+1))
    else
        echo "[$name] FAIL (rc=$rc)"
        tail -6 "$name.out" | sed 's/^/    /'
        fail=$((fail+1)); failed_list="$failed_list $name(rc=$rc)"
    fi
}

# compare_fits（无 Criterion；两个最小 FITS 实参实跑）
run_one compare_fits \
  "$CC $CFLAGS_ALL -DHAVE_WCSLIB -c -o compare_fits.o $SRC/src/tests/compare_fits.c" \
  "$CXX -o compare_fits compare_fits.o globals.o $LDFLAGS -fopenmp $CORE $KPLOT $HTMESH $LIBS $CRITERION_LIBS" \
  "./compare_fits a.fit b.fit"

# stacking_blocks_test（WITH_MAIN）
run_one stacking_blocks_test \
  "$CC $CFLAGS_ALL -DWITH_MAIN -c -o stacking_blocks_test.o $SRC/src/tests/stacking_blocks_test.c" \
  "$CXX -o stacking_blocks_test stacking_blocks_test.o globals.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# ser_test（WITH_MAIN；临时目录已重定向）
run_one ser_test \
  "$CC $CFLAGS_ALL -DWITH_MAIN -c -o ser_test.o ser_test_src.c" \
  "$CXX -o ser_test ser_test.o globals.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# siril_date_test（WITH_MAIN）
run_one siril_date_test \
  "$CC $CFLAGS_ALL -DWITH_MAIN -c -o siril_date_test.o $SRC/src/tests/siril_date_test.c" \
  "$CXX -o siril_date_test siril_date_test.o globals.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# siril_world_cs_test（WITH_MAIN）
run_one siril_world_cs_test \
  "$CC $CFLAGS_ALL -DWITH_MAIN -c -o siril_world_cs_test.o $SRC/src/tests/siril_world_cs_test.c" \
  "$CXX -o siril_world_cs_test siril_world_cs_test.o globals.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# measure_sorting（sorting_perf；自带全局变量）
run_one measure_sorting \
  "$CC $CFLAGS_ALL -c -o measure_sorting.o $SRC/src/tests/measure_sorting.c" \
  "$CXX -o measure_sorting measure_sorting.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# imoper_test（Criterion）
run_one imoper_test \
  "$CC $CFLAGS_ALL -c -o imoper_test.o $SRC/src/tests/imoper_test.c" \
  "$CXX -o imoper_test imoper_test.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# soper_test（Criterion）
run_one soper_test \
  "$CC $CFLAGS_ALL -c -o soper_test.o $SRC/src/tests/soper_test.c" \
  "$CXX -o soper_test soper_test.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# photometry_test（Criterion）
run_one photometry_test \
  "$CC $CFLAGS_ALL -c -o photometry_test.o $SRC/src/tests/photometry_test.c" \
  "$CXX -o photometry_test photometry_test.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# rejection_test（Criterion）
run_one rejection_test \
  "$CC $CFLAGS_ALL -c -o rejection_test.o $SRC/src/tests/rejection_test.c" \
  "$CXX -o rejection_test rejection_test.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

# sorting（Criterion；自带 com/gui/gfit，勿再链接 globals.o）
run_one sorting \
  "$CC $CFLAGS_ALL -c -o sorting.o $SRC/src/tests/sorting.c" \
  "$CXX -o sorting sorting.o -Wl,--unresolved-symbols=ignore-all $LDLIBS"

echo ""
echo "========== SUMMARY =========="
echo "BUILT+RUN=$ran PASS=$pass FAIL=$fail"
[ -n "$failed_list" ] && echo "FAILED:$failed_list"

# HMBS_UPSTREAM_TEST_RESULT 机器证据（HMBS 硬门禁要求）。
discovered=11
status="failed"
if [ "$ran" -eq 11 ] && [ "$fail" -eq 0 ]; then
    status="passed"
fi
result=$(printf '{"status":"%s","framework":"siril upstream unit tests (build.sh + criterion)","command":"tests/upstream_tests.sh","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":0}' \
    "$status" "$discovered" "$ran" "$pass" "$fail")
echo "$result" > upstream_test_result.json
echo "HMBS_UPSTREAM_TEST_RESULT=$result"

if [ "$status" != "passed" ]; then
    echo "[tests] 上游测试未全部通过，失败项：$failed_list"
    exit 1
fi
exit 0
