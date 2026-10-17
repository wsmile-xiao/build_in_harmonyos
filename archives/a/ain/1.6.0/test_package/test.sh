#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-ain>" >&2
    exit 2
fi

ain_bin="$1"

if [ ! -f "$ain_bin" ]; then
    echo "ain binary not found: $ain_bin" >&2
    exit 1
fi

echo "[step] Testing ain -v..."
version_output="$("$ain_bin" -v 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "1.6.0" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing ain -h..."
"$ain_bin" -h >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[ok] All tests passed."
