#!/data/service/hnp/bin/bash
# test_package/run_tests.sh — 启动器
#
# OHOS 的 /system/bin/sh（mksh）无法 exec ELF 二进制，因此用 bash 作为启动器，
# 再由**被测包内的 bin/sh** 解释执行真正的测试套件 test_dash.sh。
#
# 用法: run_tests.sh <被测 bin/sh 路径> <测试脚本路径>
set -u

SH_BIN="$1"
TEST_SCRIPT="$2"

echo "[launcher] bash=$(command -v bash)"
echo "[launcher] 被测 shell: $SH_BIN"
exec "$SH_BIN" "$TEST_SCRIPT" "$SH_BIN"
