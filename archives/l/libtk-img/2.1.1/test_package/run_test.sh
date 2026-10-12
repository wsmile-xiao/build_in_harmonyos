#!/bin/sh
# run_test.sh — libtk-img test_package 入口（R34 消费者可用性验证）
#
# 由 test_package/conanfile.py 的 test() 调用：
#     run_test.sh <tclsh> <test_script> <img_lib_dir>
#
# 调用方（conanfile.py）负责在环境中准备：
#   - LD_LIBRARY_PATH : tcl/tk/libx11 及其传递依赖（libxcb/libxau/libxdmcp）的 lib/
#   - TCLLIBPATH      : <pkg>/lib/Img<ver>（Img 运行期目录） + tcl lib + tk lib
# 本脚本只做参数/前置校验，然后 exec 真实消费者测试 test_consumer.tcl。
#
# 注意：宿主机 /bin/bash 不存在（仅 /bin/sh），故 shebang 用 sh。
set -e

TCLSH="$1"
TEST_SCRIPT="$2"
IMG_LIB_DIR="$3"

if [ -z "$TCLSH" ] || [ -z "$TEST_SCRIPT" ] || [ -z "$IMG_LIB_DIR" ]; then
    echo "FAIL: usage: run_test.sh <tclsh> <test_script> <img_lib_dir>" >&2
    exit 2
fi

if [ ! -f "$TCLSH" ]; then
    echo "FAIL: tclsh not found: $TCLSH" >&2
    exit 1
fi

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "FAIL: consumer test script missing: $TEST_SCRIPT" >&2
    exit 1
fi

if [ ! -d "$IMG_LIB_DIR" ]; then
    echo "FAIL: Img runtime dir missing: $IMG_LIB_DIR" >&2
    exit 1
fi

echo "run_test.sh: tclsh=$TCLSH"
echo "run_test.sh: img_lib_dir=$IMG_LIB_DIR"
echo "run_test.sh: LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "run_test.sh: TCLLIBPATH=$TCLLIBPATH"

exec "$TCLSH" "$TEST_SCRIPT" "$IMG_LIB_DIR"
