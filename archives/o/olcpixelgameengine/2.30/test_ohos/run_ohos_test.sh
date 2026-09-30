#!/bin/sh
# test_ohos — olcpixelgameengine 2.30 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对 OLC_PGE_HEADLESS 无头模式做独立专项检查，
# 区别于 test_package 消费者用例：本测试直接以 OHOS 工具链编译运行，
# 覆盖更多公开 API（Sprite 渐变填充/GetPixel 采样、无头 Construct、vi2d 运算、Pixel 常量）。
#
# 用法：sh run_ohos_test.sh [<OLCPGE_SRC_DIR>]
#   OLCPGE_SRC_DIR（或环境变量 OLCPGE_SRC_DIR）= 上游源码根目录（含 olcPixelGameEngine.h）
# 退出码：0=全部通过；非 0=编译或运行失败。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${1:-${OLCPGE_SRC_DIR:-}}"
if [ -z "$SRC_DIR" ]; then
    echo "FAIL: OLCPGE_SRC_DIR 未设置（参数 1 或环境变量），无法定位 olcPixelGameEngine.h"
    exit 2
fi
CXX="${OHOS_CXX:-/data/service/hnp/bin/clang++}"
BIN="$HERE/ohos_pge_test"

echo "--- olcpixelgameengine HarmonyOS 专项验证 (src=$SRC_DIR) ---"
if ! "$CXX" -std=c++17 -O2 -fPIC -I"$SRC_DIR" -pthread "$HERE/ohos_pge_test.cpp" -o "$BIN"; then
    echo "OHOS_TEST_COMPILE_FAIL=1"
    exit 1
fi
"$BIN"
rc2=$?
echo "OHOS_TEST_RUN_EXIT=$rc2"
exit "$rc2"
