#!/usr/bin/env bash
# run_harmonyos_test.sh — lightmapper 2.8 独立鸿蒙特有测试运行入口 (R02)
#
# 独立于 test_package 的构建/运行入口：使用本目录内源文件
# (harmonyos_test.c + gl_shim.c) 与 lightmapper.h 单头（取自本地 conan 包
# include 目录），在目标 OH 设备上编译并在无 GL 上下文环境运行。
#
# 用法:
#   OUT_LOG=<绝对日志路径> bash run_harmonyos_test.sh          # 正常通过路径
#   LM_NEGATIVE_PROOF=1 OUT_LOG=<abs> bash run_harmonyos_test.sh  # 负向证明路径
#
# 输出目录固定使用 $TMPDIR（必要时 $HOME/tmp），不假定 /tmp 可写。
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${TMPDIR:-$HOME/tmp}/lm-hoh-test"
TMPD="$(mktemp -d "$OUT_DIR/run.XXXXXX" 2>/dev/null || (mkdir -p "$OUT_DIR" && mktemp -d "$OUT_DIR/run.XXXXXX"))"
LOG="${OUT_LOG:-$TMPD/harmonyos_test.log}"

# 从本地 conan 包 include 目录定位 lightmapper.h（header-only 单头）
LM_HDR="$(find "$HOME/.conan2/p" -path '*/p/include/lightmapper.h' 2>/dev/null | head -1)"
if [ -z "$LM_HDR" ]; then
    echo "ERROR: lightmapper.h not found in conan cache" | tee "$LOG"
    exit 2
fi
INC_DIR="$(dirname "$LM_HDR")"
CC="/data/service/hnp/bin/clang"

{
    echo "== lightmapper 2.8 harmonyos_test =="
    echo "cwd: $(pwd)"
    echo "src: $SCRIPT_DIR/harmonyos_test.c"
    echo "header: $LM_HDR"
    echo "compiler: $($CC --version 2>&1 | head -1)"
    echo "TMPDIR: ${TMPDIR:-unset} -> OUT_DIR=$OUT_DIR"
} > "$LOG"

# 编译（独立入口：非 test_package，非 conan create test()）
"$CC" -std=c99 -Wall -Wextra -I"$INC_DIR" -I"$SCRIPT_DIR" \
    -o "$TMPD/harmonyos_test" "$SCRIPT_DIR/harmonyos_test.c" "$SCRIPT_DIR/gl_shim.c" \
    >> "$LOG" 2>&1
COMPILE_RC=$?
if [ "$COMPILE_RC" -ne 0 ]; then
    echo "COMPILE FAILED (exit $COMPILE_RC)" >> "$LOG"
    tail -25 "$LOG"
    exit 1
fi
echo "compile: ok -> $TMPD/harmonyos_test" >> "$LOG"

# 运行（无 GL 上下文环境；CPU 侧 API 断言）
"$TMPD/harmonyos_test" >> "$LOG" 2>&1
RUN_RC=$?
if [ "$RUN_RC" -ne 0 ]; then
    echo "RUN FAILED (exit $RUN_RC)" >> "$LOG"
    tail -25 "$LOG"
    exit 1
fi
echo "run: ok" >> "$LOG"
echo "LOG: $LOG"
echo "SHA256: $(sha256sum "$LOG" | awk '{print $1}')"
tail -12 "$LOG"
exit 0