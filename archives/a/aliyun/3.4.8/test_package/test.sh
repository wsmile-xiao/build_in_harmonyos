#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aliyun>" >&2
    exit 2
fi

aliyun_bin="$1"

if [ ! -f "$aliyun_bin" ]; then
    echo "aliyun binary not found: $aliyun_bin" >&2
    exit 1
fi

echo "[step] Testing aliyun --version..."
version_output="$("$aliyun_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "3.4.8" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing aliyun help..."
"$aliyun_bin" help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[ok] All tests passed."
