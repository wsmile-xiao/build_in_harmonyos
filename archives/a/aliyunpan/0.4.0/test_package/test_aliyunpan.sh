#!/usr/bin/env bash
# Consumer smoke test for the packaged aliyunpan binary.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aliyunpan>" >&2
    exit 2
fi

aliyunpan_bin="$1"

if [ ! -f "$aliyunpan_bin" ]; then
    echo "aliyunpan binary not found: $aliyunpan_bin" >&2
    exit 1
fi

echo "[step] Testing 'aliyunpan --version'..."
version_output="$("$aliyunpan_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "aliyunpan version v0.4.0" >/dev/null
echo "        [ok] version check passed (v0.4.0 embedded via ldflags)"

echo "[step] Testing 'aliyunpan help'..."
help_output="$("$aliyunpan_bin" help 2>&1)"
echo "help output (first 12 lines):"
printf '%s\n' "$help_output" | head -12
printf '%s\n' "$help_output" | grep -F "aliyunpan - 阿里云盘客户端" >/dev/null
printf '%s\n' "$help_output" | grep -F "VERSION:" >/dev/null
echo "        [ok] help check passed (app name + VERSION section present)"

echo "[ok] All consumer tests passed."
