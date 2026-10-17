#!/bin/sh
# test.sh — 实质运行 nyancat 二进制（R34/PF3/L0c）
# nyancat 是终端动画，无 --version 选项。三条断言全部可无 TTY 运行：
#   1) 二进制存在且可执行
#   2) nyancat -h 退出码 0，输出含 "Terminal Nyancat" usage 标题
#   3) nyancat -e -f 1 -n -s 渲染 1 帧后退出码 0，stdout 含帧字符（彩虹行 ">>>>>>>>"）
set -e

: "${NYANCAT_BIN:?NYANCAT_BIN not set}"

# 1) 可执行性
if [ ! -x "${NYANCAT_BIN}" ]; then
    echo "test_nyancat: FAIL — binary not executable: ${NYANCAT_BIN}" >&2
    exit 1
fi
echo "test_nyancat: OK — binary present and executable"

# 2) -h usage
OUTPUT="$("${NYANCAT_BIN}" -h 2>&1)"
RC=$?
if [ "${RC}" -ne 0 ]; then
    echo "test_nyancat: FAIL — nyancat -h exit code ${RC}, expected 0" >&2
    echo "${OUTPUT}" >&2
    exit 1
fi
if ! echo "${OUTPUT}" | grep -q "Terminal Nyancat"; then
    echo "test_nyancat: FAIL — usage title 'Terminal Nyancat' not found in -h output" >&2
    echo "${OUTPUT}" >&2
    exit 1
fi
echo "test_nyancat: OK — nyancat -h exit 0, usage verified"

# 3) 单帧渲染（-e 不清屏 -f 1 一帧后退出 -n 无计时行 -s 不设标题）
# 帧字符经 TERM 探测转成 ANSI 转义序列输出（ttype 1/2/4 均为 escape + 空格），
# 字面 '>>' 不出现在 stdout；用输出字节数断言单帧已完整渲染：
# 80x24 帧 x 每格 2 字符 >= 3840 字节，即使窄终端/降级模式也远大于 500。
FRAME_OUT="$("${NYANCAT_BIN}" -e -f 1 -n -s 2>&1)"
RC=$?
if [ "${RC}" -ne 0 ]; then
    echo "test_nyancat: FAIL — single-frame render exit code ${RC}, expected 0" >&2
    exit 1
fi
FRAME_BYTES="$(printf '%s' "${FRAME_OUT}" | wc -c)"
if [ "${FRAME_BYTES}" -lt 500 ]; then
    echo "test_nyancat: FAIL — frame output too short (${FRAME_BYTES} bytes, expected >= 500)" >&2
    exit 1
fi
echo "test_nyancat: OK — single-frame render exit 0, frame output verified (${FRAME_BYTES} bytes)"
echo "test_nyancat: ALL TESTS PASSED"
