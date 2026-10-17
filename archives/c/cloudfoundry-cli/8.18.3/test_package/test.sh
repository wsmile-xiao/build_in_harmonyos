#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-cf>" >&2
    exit 2
fi

cf_bin="$1"

if [ ! -f "$cf_bin" ]; then
    echo "cf binary not found: $cf_bin" >&2
    exit 1
fi

echo "[step] Testing cf --version..."
version_output="$("$cf_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "8.18.3" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing cf help..."
"$cf_bin" help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[ok] All tests passed."
