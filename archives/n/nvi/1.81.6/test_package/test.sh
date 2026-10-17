#!/bin/sh
# test.sh — 实质运行 nvi vi 二进制（R34/PF3）
# 用 `vi -e -s` + stdin ex 命令驱动（nvi 无 --version 选项）：
#   1. 创建临时文件 test_nvi.txt，内容含 "nvi"
#   2. 通过 stdin 喂 ex 命令 `s/nvi/nvi-ok/` 与 `wq`
#   3. 验证写回文件内容包含 "nvi-ok"
# TERM=dumb 避免 tty 依赖；TERMINFO 由 ncurses runenv 注入（env="conanrun"）。
set -e

: "${VI_BIN:?VI_BIN not set}"
: "${TEST_WORKDIR:?TEST_WORKDIR not set}"

TEST_FILE="${TEST_WORKDIR}/test_nvi.txt"
printf 'hello nvi 1.81.6\n' > "${TEST_FILE}"

# ex 脚本模式：s/nvi/nvi-ok/ 替换第一处，wq 写回并退出
printf 's/nvi/nvi-ok/\nwq\n' | TERM=dumb "${VI_BIN}" -e -s "${TEST_FILE}"

if grep -q 'nvi-ok' "${TEST_FILE}"; then
    echo "test_nvi: OK — vi -e -s substitution + write-back verified"
    echo "content: $(cat "${TEST_FILE}")"
else
    echo "test_nvi: FAIL — expected 'nvi-ok' in ${TEST_FILE}, got:" >&2
    cat "${TEST_FILE}" >&2
    exit 1
fi
