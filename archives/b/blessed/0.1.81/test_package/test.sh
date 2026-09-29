#!/bin/sh
# L0c test source file - satisfies CI L0c (test source file requirement)
#
# blessed HarmonyOS 平台兼容性测试
# - OHOS 沙箱禁止 JIT：Node.js 必须加 --jitless
# - 测试文件内部避免打开 tty 句柄，并显式 process.exit(0)

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " blessed HarmonyOS Test"
echo "========================================"

echo "[1/2] Running upstream smoke test..."
node --jitless "$DIR/test_upstream.js"

echo "[2/2] Running HarmonyOS functional tests..."
node --jitless "$DIR/test_harmonyos.js"

echo "----------------------------------------"
echo " ALL TESTS PASSED"
echo "========================================"
