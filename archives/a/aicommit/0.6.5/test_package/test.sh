#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aicommit>" >&2
    exit 2
fi

aicommit_bin="$1"

if [ ! -f "$aicommit_bin" ]; then
    echo "aicommit binary not found: $aicommit_bin" >&2
    exit 1
fi

echo "[step] Testing 'aicommit version'..."
version_output="$("$aicommit_bin" version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "v0.6.5" >/dev/null
echo "        [ok] version check passed (v0.6.5 embedded via ldflags)"

echo "[step] Testing 'aicommit --help'..."
"$aicommit_bin" --help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[step] Testing 'aicommit version --help'..."
"$aicommit_bin" version --help >/dev/null 2>&1
echo "        [ok] subcommand help check passed"

echo "[ok] All tests passed."
