#!/bin/sh
# run_ohos_tests.sh — imlib2-heic 0.1.1 鸿蒙专项测试 + 消费者测试复现脚本
#
# 仓库内不提交二进制/ELF：example.heic 以 base64 文本（example.heic.b64）
# 保存（同 imlib2-1.9.1 images.b64.txt 先例），heic.so 来自安装包
# （lib/imlib2/loaders/heic.so，已 ELF 自签）。
#
# 用法: run_ohos_tests.sh <heic.so 绝对路径> [工作目录]
set -u

HEIC_SO="${1:?usage: run_ohos_tests.sh <heic.so> [workdir]}"
WORKDIR="${2:-$(cd "$(dirname "$0")" && pwd)}"
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
B64="${TESTS_DIR}/example.heic.b64"

cd "$WORKDIR" || exit 2

# 1. 解码真实 HEIC 样本（b64 → 二进制）
[ -f "$B64" ] || { echo "missing $B64"; exit 2; }
if command -v base64 >/dev/null 2>&1; then
    base64 -d "$B64" > example.heic || { echo "b64 decode failed"; exit 2; }
else
    python3 -c "import base64,sys;sys.stdout.buffer.write(base64.b64decode(open('$B64').read()))" > example.heic || exit 2
fi
echo "fixture decoded: $(ls -la example.heic | awk '{print $5}') bytes"

# 2. 编译两个测试（clang, arm64; -DX_DISPLAY_MISSING 跳过 X11 头）
#    头文件：上游源码目录(imlib2_common.h/loader.h) + imlib2 包 include
SRC="$(find /storage/Users/currentUser/tmp/builds -maxdepth 3 -type d -name 'imlib2-heic-0.1.1' 2>/dev/null | head -1)"
# Imlib2.h 来自依赖 imlib2/1.9.1 包（非本插件包；本插件包不装头文件）。
# 由 IMLIB2_INCLUDE 显式传入（复验命令给出），或按 conan 缓存布局探测。
IMLIB_INC="${IMLIB2_INCLUDE:-}"
if [ -z "$IMLIB_INC" ]; then
    IMLIB_INC="$(find /storage/Users/currentUser/.conan2/p -maxdepth 3 -path '*/p/include' -type d 2>/dev/null | while read d; do [ -f "$d/Imlib2.h" ] && echo "$d" && break; done | head -1)"
fi
[ -n "$IMLIB_INC" ] || { echo "cannot locate Imlib2.h; set IMLIB2_INCLUDE"; exit 2; }
CC=/data/service/hnp/bin/clang
$CC -std=c11 -DX_DISPLAY_MISSING -I"$SRC" -I"$IMLIB_INC" \
    -o test_ohos_loader "${TESTS_DIR}/test_ohos_loader.c" || { echo "build test_ohos_loader failed"; exit 2; }
$CC -std=c11 -DX_DISPLAY_MISSING -I"$SRC" -I"$IMLIB_INC" \
    -o consumer_heic_host "${TESTS_DIR}/consumer_heic_host.c" || { echo "build consumer failed"; exit 2; }
echo "tests built"

# 3. 运行（依赖库路径由调用方 LD_LIBRARY_PATH 提供）
./test_ohos_loader "$HEIC_SO" ./example.heic
rc1=$?
./consumer_heic_host "$HEIC_SO" ./example.heic
rc2=$?
echo "=== summary: hos_test=$rc1 consumer_test=$rc2 ==="
[ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ]
