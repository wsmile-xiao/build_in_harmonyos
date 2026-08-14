#!/system/bin/sh
# acepack test_package 运行器（OHOS aarch64）
# 用法: run_test.sh <acepack_package_folder> <rscript> <test_acepack.R>
set -euo pipefail
PKG_FOLDER="$1"
RSCRIPT="$2"
TEST_SCRIPT="$3"
TP_DIR="$(dirname "$0")"

R_LIB="$PKG_FOLDER/lib/R/library"
if [ ! -d "$R_LIB/acepack" ]; then
    echo "ACEPACK_TEST_FAIL: acepack 包不在 R library 树: $R_LIB" >&2
    exit 66
fi

export R_LIBS="$R_LIB"
# P2 修复：set -e 会使失败直接退出，导致下方 rc=$? 自定义错误处理不可达；
# 改用 || 短路，set -e 不触发提前退出，保留自定义 ACEPACK_TEST_FAIL 诊断。
"$RSCRIPT" "$TEST_SCRIPT" || {
    rc=$?
    echo "ACEPACK_TEST_FAIL: Rscript 退出码 $rc" >&2
    exit $rc
}
echo "ACEPACK_TEST_PASS"

# 上游测试（base R 兼容层，方案二：如实标注统计与明细，不伪造通过）
echo "ACEPACK_UPSTREAM_TESTS_BEGIN"
"$RSCRIPT" "$TP_DIR/run_upstream_tests.R" "$TP_DIR" || {
    rc=$?
    echo "ACEPACK_UPSTREAM_TEST_FAIL: Rscript 退出码 $rc" >&2
    exit $rc
}
exit 0
