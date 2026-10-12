#!/system/bin/sh
# test_upstream_boost_test.sh — 官方上游 Boost.Test ts-suite harness（boost 1.89.0）
#
# 背景：
#   b2 构建系统在 OHOS 上不兼容（bootstrap.sh 工具链白名单无 OHOS，E068/E099），
#   上游 libs/test/build/CMakeLists.txt 的独立构建在 OHOS 交叉环境同样不适用
#   （check_cxx_compiler_flag 强加 -std=c++11，R04：C++11 下 fp-multiprecision
#   系列编译失败）。
#   本 harness 用 clang++ 直编上游 libs/test/src 的 19 个 Boost.Test 源
#   （默认 init API，与上游 CMake boost_test_framework 目标一致：全局
#   -DBOOST_TEST_NO_LIB，无 BOOST_TEST_ALTERNATIVE_INIT_API），再编译并真实运行
#   libs/test/test 下官方 ts-suite：7 个 suite / 73 个单文件用例 +
#   datasets 12-TU 单可执行 = 74 个可执行，与上游
#   libs/test/test/CMakeLists.txt 的 bt-unittest-* 测试集合逐一对应。
#
#   本脚本是 conanfile.py build() 内嵌上游 runner 的手动复现路径
#   （同标志、同用例集、同判定语义）；CI/finish 链路以 conan create 为准。
#
# 判定语义（与配方内嵌 runner 一致）：
#   - test-timeout-fail / test-timeout-suite-fail 在上游 Jamfile.v2 L185/L187
#     标注 run-fail（用例预期失败）：rc!=0 记 EXPECTED_FAIL_PASS，rc=0 记
#     UNEXPECTED_PASS（异常）；
#   - 其余用例：rc==0 记 PASS，否则记 FAIL 并附 rc 值；
#   - 运行时注入 SDK libc++ 目录到 LD_LIBRARY_PATH（-print-file-name 自省，
#     防 rc=127，1.85.0 先例）。
#
# 用法：
#   sh test_upstream_boost_test.sh <verified_source_root> [work_dir]
#   例：sh test_upstream_boost_test.sh /storage/Users/currentUser/.conan2/p/boost1e883b6e252a4/s

set -u

SRC="${1:?usage: test_upstream_boost_test.sh <verified_source_root> [work_dir]}"
BASE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SRC/boost/version.hpp" ]; then
    echo "ERROR: verified source root invalid: $SRC" >&2
    exit 2
fi
if [ ! -d "$SRC/libs/test/test" ]; then
    echo "ERROR: libs/test/test missing in $SRC" >&2
    exit 2
fi

WORK="${2:-$BASE/reports/ts-suite-run}"
rm -rf "$WORK"
mkdir -p "$WORK/lib" "$WORK/exe" "$BASE/reports"

CXX=/data/service/hnp/bin/clang++
AR=/data/service/hnp/bin/llvm-ar

INC_TEST="-I$SRC/libs/test/include"
INC_ROOT="-I$SRC"

REPORT="$BASE/reports/upstream-ts-suite-report.txt"

echo "=== build upstream Boost.Test static lib (default init API, C++17) ==="
LIBFLAGS="-std=c++17 -O2 -DNDEBUG -DBOOST_TEST_NO_LIB"
LIB_OK=1
for n in compiler_log_formatter debug decorator execution_monitor framework \
         junit_log_formatter plain_report_formatter progress_monitor \
         results_collector results_reporter test_framework_init_observer \
         test_tools test_tree unit_test_log unit_test_main unit_test_monitor \
         unit_test_parameters xml_log_formatter xml_report_formatter; do
    echo "  [lib] $n.cpp"
    "$CXX" $LIBFLAGS $INC_TEST $INC_ROOT -c "$SRC/libs/test/src/$n.cpp" \
        -o "$WORK/lib/$n.o" 2>>"$WORK/lib-build.log" || LIB_OK=0
done
"$AR" rcs "$WORK/lib/libboost_test_framework.a" "$WORK"/lib/*.o \
    2>>"$WORK/lib-build.log" || LIB_OK=0
if [ "$LIB_OK" -ne 1 ]; then
    echo "HARNESS_ABORT: test library build failed (see $WORK/lib-build.log)"
    exit 3
fi
echo "LIB_BUILD_OK"

# 运行时库路径（注入 SDK libc++ 共享库目录）
LIBCXX="$("$CXX" -print-file-name=libc++_shared.so 2>/dev/null | tail -1)"
RUNENV=""
case "$LIBCXX" in
    /*) RUNENV="LD_LIBRARY_PATH=$(dirname "$LIBCXX")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}";;
esac
echo "RUNENV=$RUNENV"

TESTFLAGS="-std=c++17 -O2 -DBOOST_TEST_NO_LIB"
PASS=0
FAIL=0
EXFAIL=0
: > "$REPORT"

run_one() {
    # $1=label $2=expected_fail(0/1) 剩余参数=源文件
    label="$1"
    exp="$2"
    shift 2
    exe_name=$(printf '%s' "$label" | tr '/ ' '__')
    case "$exe_name" in
        *.cpp) exe_name="${exe_name%.cpp}";;
    esac
    exe="$WORK/exe/$exe_name"
    if ! "$CXX" $TESTFLAGS $INC_TEST $INC_ROOT "$@" \
        "$WORK/lib/libboost_test_framework.a" -o "$exe" \
        2>"$WORK/compile-$exe_name.log"; then
        echo "COMPILE_FAIL $label" >> "$REPORT"
        FAIL=$((FAIL + 1))
        return
    fi
    if env $RUNENV timeout 120 "$exe" > "$WORK/run-$exe_name.log" 2>&1; then
        rc=0
    else
        rc=$?
    fi
    if [ "$exp" = "1" ]; then
        if [ $rc -ne 0 ]; then
            echo "EXPECTED_FAIL_PASS $label rc=$rc (upstream Jamfile run-fail, failure is the intended result)" >> "$REPORT"
            PASS=$((PASS + 1))
            EXFAIL=$((EXFAIL + 1))
        else
            echo "UNEXPECTED_PASS $label rc=0 (expected failure per upstream run-fail marker)" >> "$REPORT"
            FAIL=$((FAIL + 1))
        fi
    else
        if [ $rc -eq 0 ]; then
            echo "PASS $label rc=0" >> "$REPORT"
            PASS=$((PASS + 1))
        else
            echo "FAIL $label rc=$rc" >> "$REPORT"
            FAIL=$((FAIL + 1))
        fi
    fi
}

echo "=== compile + run official Boost.Test ts-suite (74 executables) ==="
for suite in writing-test-ts execution_monitor-ts framework-ts \
             usage-variants-ts utils-ts test-organization-ts smoke-ts; do
    for f in "$SRC/libs/test/test/$suite"/*.cpp; do
        [ -e "$f" ] || continue
        base=$(basename "$f" .cpp)
        exp=0
        case "$suite/$base" in
            writing-test-ts/test-timeout-fail | writing-test-ts/test-timeout-suite-fail)
                exp=1
                ;;
        esac
        run_one "$suite/$base.cpp" "$exp" "$f"
    done
done

# datasets multi-TU test: 12 .cpp translation units -> one executable
# (upstream CMake target boost_test_datasets)
run_one "test-organization-ts/datasets-test (12 TUs)" 0 \
    "$SRC"/libs/test/test/test-organization-ts/datasets-test/*.cpp

echo "TOTAL $((PASS + FAIL)): $PASS passed / $FAIL failed (expected-fail counted in passed: $EXFAIL)" | tee -a "$REPORT"
echo "REPORT: $REPORT"
[ "$FAIL" -eq 0 ]
