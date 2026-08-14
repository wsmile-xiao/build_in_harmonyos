#!/usr/bin/env bash
# test_package/test.sh — Verify arelo version output and help subcommand
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-arelo>" >&2
    exit 2
fi

arelo_bin="$1"

if [ ! -f "$arelo_bin" ]; then
    echo "arelo binary not found: $arelo_bin" >&2
    exit 1
fi

# Verify version output
version_output="$("$arelo_bin" --version 2>&1 || true)"
printf '%s\n' "$version_output"

# Verify help works (should show usage)
help_output="$("$arelo_bin" --help 2>&1 || true)"
printf '%s\n' "$help_output" | grep -F "Usage:" >/dev/null

# Verify the binary can detect its version (even if "devel" from non-release build)
printf '%s\n' "$version_output" | grep -F "arelo" >/dev/null

echo "=== All tests passed ==="
