#!/usr/bin/env bash
# test.sh — smoke test for ClangBuildAnalyzer binary
# Usage: bash test.sh /path/to/ClangBuildAnalyzer
#
# R34: 实质依赖被测包的二进制 —— 运行 --version 并校验输出。
# 期望: 退出码 0 且输出包含 "ClangBuildAnalyzer" 与 "1.6.0"。
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 /path/to/ClangBuildAnalyzer" >&2
    exit 2
fi

binary="$1"

# 1. 运行 --version。临时关闭 set -e 以捕获非零退出码。
set +e
output="$("$binary" --version 2>&1)"
exit_code=$?
set -e

if [[ $exit_code -ne 0 ]]; then
    echo "ERROR: --version returned exit code $exit_code" >&2
    echo "--- output:" >&2
    echo "$output" >&2
    exit 1
fi

# 2. 校验输出包含期望字符串
if [[ "$output" != *"ClangBuildAnalyzer"* ]]; then
    echo "ERROR: --version output missing 'ClangBuildAnalyzer'" >&2
    echo "--- output:" >&2
    echo "$output" >&2
    exit 1
fi

if [[ "$output" != *"1.6.0"* ]]; then
    echo "ERROR: --version output missing '1.6.0'" >&2
    echo "--- output:" >&2
    echo "$output" >&2
    exit 1
fi

echo "$output"
exit 0
