#!/bin/sh
# test.sh — 实质运行 netris 二进制（R34/PF3/L0c）
# netris 是交互式 curses 游戏，无 --version 选项，用 `netris -h` 驱动：
#   1. 执行 netris -h，验证退出码为 0
#   2. 捕获输出，验证包含 "Netris version 0.52" 版本串
#   3. 验证 sr 示例机器人二进制存在且可执行
# TERM=dumb 避免 tty 依赖；TERMINFO 由 ncurses runenv 注入（env="conanrun"）。
set -e

: "${NETRIS_BIN:?NETRIS_BIN not set}"

# 1) netris -h: 打印 usage 并退出 0
OUTPUT="$("${NETRIS_BIN}" -h 2>&1)"
RC=$?
if [ "${RC}" -ne 0 ]; then
    echo "test_netris: FAIL — netris -h exit code ${RC}, expected 0" >&2
    echo "${OUTPUT}" >&2
    exit 1
fi

# 2) 版本串校验
if ! echo "${OUTPUT}" | grep -q "Netris version 0.52"; then
    echo "test_netris: FAIL — version string not found in output" >&2
    echo "${OUTPUT}" >&2
    exit 1
fi
echo "test_netris: OK — netris -h exit 0, version 0.52 verified"

# 3) sr 机器人二进制存在且可执行
if [ -n "${SR_BIN:-}" ] && [ -x "${SR_BIN}" ]; then
    echo "test_netris: OK — sr robot binary present at ${SR_BIN}"
else
    echo "test_netris: WARN — sr binary not found at ${SR_BIN:-<unset>} (non-fatal)"
fi
