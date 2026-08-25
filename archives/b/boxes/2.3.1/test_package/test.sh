#!/usr/bin/env sh
# test_package/test.sh — 真实调用 boxes 二进制的消费者测试
# 由 test_package/conanfile.py 调用：sh test.sh <path-to-boxes>
#
# 4 个真实用例（boxes 是文本过滤器，通过 stdin->stdout 验证核心逻辑）：
#   1. 简单画框：echo Hello | boxes 输出含 box 边框
#   2. 指定设计 -d shell：输出含 shell 风格边框
#   3. 移除盒子：boxes | boxes -r 还原为纯文本
#   4. --version 输出含 "2.3.1"
#
# 说明：OHOS 上 boxes 经 stdin 管道调用会报 "terminals database is
# inaccessible" 并失败，但用临时输入文件（`boxes < file`，与上游 testrunner.sh
# 相同的方式）则正常绘制。因此本脚本用临时文件喂 stdin。
#
# 每个用例独立计数，结束后输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记。
# 任一失败则退出码 1，避免静默通过。
set -u

TMPROOT="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
cd "$TMPROOT" 2>/dev/null || cd / 2>/dev/null || true

# boxes draws via ncurses setupterm; a TERM with a visible terminfo entry is
# required on OHOS so the drawing path does not abort.
export TERM="${TERM:-xterm}"

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-boxes>" >&2
    exit 2
fi

boxes_bin="$1"
PASS=0
FAIL=0
INPUT_FILE="$TMPROOT/boxes-tp-input-$$.txt"
trap 'rm -f "$INPUT_FILE"' EXIT

if [ ! -f "$boxes_bin" ]; then
    echo "boxes binary not found: $boxes_bin" >&2
    exit 1
fi

# ── 用例 1: 简单画框 ──
echo "[case 1/4] echo Hello | boxes"
printf 'Hello\n' > "$INPUT_FILE"
frame_output="$("$boxes_bin" < "$INPUT_FILE" 2>&1)"
echo "  output: $(printf '%s' "$frame_output" | tr '\n' ' ')"
if printf '%s\n' "$frame_output" | grep -F "Hello" >/dev/null && \
   printf '%s\n' "$frame_output" | grep -F "/" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] box frame drawn around text"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] no box frame in output"
fi

# ── 用例 2: 指定设计 -d shell ──
echo "[case 2/4] echo Test | boxes -d shell"
printf 'Test\n' > "$INPUT_FILE"
shell_output="$("$boxes_bin" -d shell < "$INPUT_FILE" 2>&1)"
echo "  output: $(printf '%s' "$shell_output" | tr '\n' ' ')"
# The shell design is a single-line comment style using '#' framing chars.
if printf '%s\n' "$shell_output" | grep -F "Test" >/dev/null && \
   printf '%s\n' "$shell_output" | grep -F "#" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] shell design produced a #-framed box"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] shell design output unexpected"
fi

# ── 用例 3: 移除盒子 ──
echo "[case 3/4] boxes | boxes -r"
printf 'The quick brown fox\n' > "$INPUT_FILE"
drawn="$("$boxes_bin" < "$INPUT_FILE" 2>&1)"
printf '%s\n' "$drawn" > "$INPUT_FILE"
removed="$("$boxes_bin" -r < "$INPUT_FILE" 2>&1)"
echo "  removed: $(printf '%s' "$removed" | tr '\n' ' ')"
# 只 grep 原文不足以判定：-r 若静默不做事（原样回显带边框的输入）同样命中，
# 移除逻辑坏掉照样 PASS。追加「输出不得残留边框字符」才能真正检出回归。
if printf '%s\n' "$removed" | grep -F "The quick brown fox" >/dev/null \
   && ! printf '%s\n' "$removed" | grep -qE '[/\\|+*_-]{2,}'; then
    PASS=$((PASS + 1))
    echo "  [ok] box removed correctly (no border residue)"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] box removal left border residue or lost text"
fi

# ── 用例 4: --version ──
echo "[case 4/4] boxes --version"
ver_output="$("$boxes_bin" --version 2>&1)"
echo "  output: $ver_output"
if printf '%s\n' "$ver_output" | grep -F "2.3.1" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] version contains 2.3.1"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] version output does not contain 2.3.1"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <boxes-bin>\",\"discovered\":4,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"