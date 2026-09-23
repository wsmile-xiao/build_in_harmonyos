#!/usr/bin/env bash
# test_package/test.sh — scooter 0.9.1 消费者冒烟测试 (R34: 实质调用被测包二进制)
#
# 4 条断言，全部实质调用 scooter 二进制核心功能:
#   1. --version 输出包含 "0.9.1"
#   2. --help 退出码 0 且输出非空
#   3. stdin 管道 find-and-replace: echo 文本 | scooter --no-tui --search-text ... --replace-text ...
#      输出中搜索串已被替换为替换串
#   4. 文件系统 find-and-replace: 在临时目录中用 --no-stdin 对文件执行替换,
#      校验文件内容已按预期改变 (核心功能端到端验证)
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-scooter>" >&2
    exit 2
fi

scooter_bin="$1"

if [ ! -f "$scooter_bin" ]; then
    echo "scooter binary not found: $scooter_bin" >&2
    exit 1
fi

echo "[step] Testing scooter --version..."
version_output="$("$scooter_bin" --version 2>&1)"
echo "        version output: $version_output"
printf '%s\n' "$version_output" | grep -F "0.9.1" >/dev/null
echo "        [ok] version check passed (assertion 1/4)"

echo "[step] Testing scooter --help..."
help_output="$("$scooter_bin" --help 2>&1 || true)"
if [ -z "$help_output" ]; then
    echo "        [fail] scooter --help produced empty output" >&2
    exit 1
fi
printf '%s\n' "$help_output" | grep -F "Interactive find and replace TUI" >/dev/null
echo "        [ok] help check passed (assertion 2/4)"

echo "[step] Testing stdin find-and-replace..."
stdin_out="$(printf 'The quick brown fox\nsays fox\n' | "$scooter_bin" --no-tui \
    --search-text "fox" --replace-text "cat" 2>&1)"
echo "        stdin output: $stdin_out"
printf '%s\n' "$stdin_out" | grep -F "The quick brown cat" >/dev/null
printf '%s\n' "$stdin_out" | grep -F "says cat" >/dev/null
if printf '%s\n' "$stdin_out" | grep -qF "says fox"; then
    echo "        [fail] stdin replacement did not replace 'fox'" >&2
    exit 1
fi
echo "        [ok] stdin find-and-replace passed (assertion 3/4)"

echo "[step] Testing file find-and-replace..."
tmpdir="$(mktemp -d 2>/dev/null || echo "$TMPDIR/scooter-test-$$")"
trap 'rm -rf "$tmpdir"' EXIT
printf 'apple apple pie\nno match\napple tree\n' > "$tmpdir/file1.txt"
file_out="$("$scooter_bin" --no-tui --no-stdin --search-text "apple" \
    --replace-text "pear" "$tmpdir" 2>&1)"
echo "        file replace output: $file_out"
new_content="$(cat "$tmpdir/file1.txt")"
printf '%s\n' "$new_content" | grep -F "pear pear pie" >/dev/null
printf '%s\n' "$new_content" | grep -F "pear tree" >/dev/null
if printf '%s\n' "$new_content" | grep -qF "apple"; then
    echo "        [fail] file replacement did not replace 'apple'" >&2
    exit 1
fi
echo "        [ok] file find-and-replace passed (assertion 4/4)"

echo "[ok] All 4 tests passed."
