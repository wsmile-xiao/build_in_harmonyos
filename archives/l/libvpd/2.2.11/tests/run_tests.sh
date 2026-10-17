#!/bin/sh
# run_tests.sh — 针对已安装产物编译并运行消费者/鸿蒙专项测试
# 用法: run_tests.sh <prefix>   (prefix 为 libvpd 安装前缀, 头文件在 <prefix>/include)
# 输出退出码到 stdout, 任一失败以非零退出。
set -u
PREFIX="${1:?usage: run_tests.sh <prefix>}"
CC="${CC:-/data/service/hnp/bin/clang}"
CXX="${CXX:-/data/service/hnp/bin/clang++}"
TMPDIR_DIR="${TMPDIR:-/storage/Users/currentUser/tmp}"
SQLITE3_PREFIX="${SQLITE3_PREFIX:-/storage/Users/currentUser/.conan2/p/sqlitdf7366e04b088/p}"

INCDIR="$PREFIX/include"
LIBDIR="$PREFIX/lib"
SQL_INC="$SQLITE3_PREFIX/include"
SQL_LIB="$SQLITE3_PREFIX/lib"
OUT="$TMPDIR_DIR/libvpd-tests"

mkdir -p "$OUT" || exit 1
FAIL=0

# 消费者验证 1: C API（动态链接 libvpd.so + sqlite3）
"$CC" -I"$INCDIR" -I"$SQL_INC" "$(dirname "$0")/consumer_c.c" \
    -L"$LIBDIR" -L"$SQL_LIB" -lvpd -lsqlite3 -o "$OUT/consumer_c" 2>"$OUT/consumer_c.build.log"
if [ $? -ne 0 ]; then echo "consumer_c BUILD FAIL"; cat "$OUT/consumer_c.build.log"; FAIL=1; else
    LD_LIBRARY_PATH="$LIBDIR:$SQL_LIB" "$OUT/consumer_c" 2>&1 || { echo "consumer_c RUN FAIL"; FAIL=1; }
fi

# 消费者验证 2: C++ API（动态链接 libvpd_cxx.so + libvpd.so + sqlite3）
"$CXX" -I"$INCDIR" -I"$SQL_INC" "$(dirname "$0")/consumer_cpp.cpp" \
    -L"$LIBDIR" -L"$SQL_LIB" -lvpd_cxx -lvpd -lsqlite3 \
    -o "$OUT/consumer_cpp" 2>"$OUT/consumer_cpp.build.log"
if [ $? -ne 0 ]; then echo "consumer_cpp BUILD FAIL"; cat "$OUT/consumer_cpp.build.log"; FAIL=1; else
    LD_LIBRARY_PATH="$LIBDIR:$SQL_LIB" "$OUT/consumer_cpp" 2>&1 || { echo "consumer_cpp RUN FAIL"; FAIL=1; }
fi

# HarmonyOS 专项测试（动态链接 + dlopen 检查共享库运行期产物）
"$CXX" -I"$INCDIR" -I"$SQL_INC" "$(dirname "$0")/ohos_specific_test.cpp" \
    -L"$LIBDIR" -L"$SQL_LIB" -lvpd_cxx -lvpd -lsqlite3 -ldl \
    -o "$OUT/ohos_specific_test" 2>"$OUT/ohos_specific.build.log"
if [ $? -ne 0 ]; then echo "ohos_specific BUILD FAIL"; cat "$OUT/ohos_specific.build.log"; FAIL=1; else
    LD_LIBRARY_PATH="$LIBDIR:$SQL_LIB" "$OUT/ohos_specific_test" 2>&1 || { echo "ohos_specific RUN FAIL"; FAIL=1; }
fi

if [ "$FAIL" -eq 0 ]; then echo "ALL_TESTS_PASS"; else echo "SOME_TESTS_FAIL"; fi
exit "$FAIL"