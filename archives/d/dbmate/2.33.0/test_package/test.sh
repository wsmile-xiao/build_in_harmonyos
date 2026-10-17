#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-dbmate>" >&2
    exit 2
fi

dbmate_bin="$1"

if [ ! -f "$dbmate_bin" ]; then
    echo "dbmate binary not found: $dbmate_bin" >&2
    exit 1
fi

echo "[step] Testing dbmate --version..."
version_output="$("$dbmate_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "2.33.0" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing dbmate help..."
"$dbmate_bin" --help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[ok] All tests passed."
