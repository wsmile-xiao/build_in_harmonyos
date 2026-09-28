#!/usr/bin/env bash
# run_ohos_test.sh — 编译并运行 fft-c 的 HarmonyOS PC 专项测试
# 使用 OHOS 工具链（/data/service/hnp/bin/clang, target aarch64-unknown-linux-ohos）
set -u
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM_SRC="${UPSTREAM_SRC:-$HOME/tmp/fft-c-src/fft-c-3356ecd87d}"
CLANG="${CLANG:-/data/service/hnp/bin/clang}"
OUT="${OUT:-$SRC_DIR/ohos_fft_test}"
LOG="${LOG:-$SRC_DIR/ohos_fft_test_run.log}"

echo "[run_ohos_test] clang: $CLANG"
echo "[run_ohos_test] upstream src: $UPSTREAM_SRC"

# 1) 编译：专项测试 + 上游 fft.c 一起链接
"$CLANG" -O2 -Wall -Wextra -I"$UPSTREAM_SRC" -o "$OUT" "$SRC_DIR/ohos_fft_test.c" "$UPSTREAM_SRC/fft.c" -lm
rc=$?
if [ $rc -ne 0 ]; then
    echo "[run_ohos_test] COMPILE FAILED rc=$rc" >&2
    exit $rc
fi
echo "[run_ohos_test] compile OK"

# 2) 运行（重定向到日志，同时保留 stdout 供采集）
"$OUT" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo "[run_ohos_test] run exit=$rc log=$LOG"
exit $rc
