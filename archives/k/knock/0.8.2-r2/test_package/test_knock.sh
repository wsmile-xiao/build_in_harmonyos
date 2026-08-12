#!/usr/bin/env bash
set -euo pipefail
# test_package/test_knock.sh — knock 二进制 smoke test
#
# 实质依赖被测包（R34）：通过执行 knock 二进制并断言其输出验证适配正确性。
# 由 test_package/conanfile.py 的 test() 调用。
# 失败时打印诊断信息（knock 真实输出+退出码）便于定位。

KNOCK_BIN="${1:-knock}"

if [ ! -x "$KNOCK_BIN" ]; then
    echo "FAIL: knock binary not executable at $KNOCK_BIN" >&2
    ls -la "$KNOCK_BIN" >&2
    exit 1
fi

# 断言 1：knock --version 可执行且输出包含 "knock"
# set -e 下用 `|| version_rc=$?` 捕获非零退出码，避免脚本提前退出
version_rc=0
version_out=$("$KNOCK_BIN" --version 2>&1) || version_rc=$?
echo "knock --version output: $version_out"
echo "knock --version exit code: $version_rc"
if [ "$version_rc" -ne 0 ]; then
    echo "FAIL: knock --version exited with $version_rc (可能 OHOS 安全弹窗 R7 或二进制无法执行)" >&2
    exit 1
fi
echo "$version_out" | grep -q "knock" || { echo "FAIL: --version 输出不含 'knock': $version_out" >&2; exit 1; }

# 断言 2：knock --help 输出包含 usage 行
# 注：上游 knock 的 --help/-h 经 usage() 后 exit(1)（knock.c case 'h' fallthrough 到 exit(1)），
# 这是上游设计（usage 打印后非0退出），不视为失败。只验证输出内容。
help_rc=0
help_out=$("$KNOCK_BIN" --help 2>&1) || help_rc=$?
echo "knock --help exit code: $help_rc (上游 usage() 退出码为 1，属正常)"
echo "$help_out" | grep -q "usage" || { echo "FAIL: --help 输出不含 'usage': $help_out" >&2; exit 1; }

echo "PASS: knock --version 和 --help 验证通过"
