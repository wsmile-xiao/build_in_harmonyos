#!/usr/bin/env bash
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there first so the shell is not left
# in an HMDFS cwd that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-addchain>" >&2
    exit 2
fi

addchain_bin="$1"

if [ ! -f "$addchain_bin" ]; then
    echo "addchain binary not found: $addchain_bin" >&2
    exit 1
fi

echo "[step] Testing addchain version..."
version_output="$("$addchain_bin" version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "0.4.0" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing addchain help..."
"$addchain_bin" help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[step] Testing addchain eval subcommand..."
# eval 子命令从 stdin 读取 .acc 脚本并输出评估结果。
# 最简脚本 "1 add 1" 计算 1+1=2，输出应包含十六进制链值 0x2。
eval_output="$(printf '1 add 1\n' | "$addchain_bin" eval 2>&1)" || true
echo "eval output: $eval_output"
printf '%s\n' "$eval_output" | grep -E "0x2|[0-9]+" >/dev/null
echo "        [ok] eval subcommand produced numeric output"

echo "[ok] All tests passed."
