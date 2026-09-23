#!/usr/bin/env bash
set -euo pipefail

exe="${1:-}"
if [ -z "$exe" ] || [ ! -x "$exe" ]; then
    echo "algobox executable is missing or is not executable: $exe" >&2
    exit 1
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QTWEBENGINE_DISABLE_SANDBOX=1

version_output="$("$exe" --version 2>&1)"
printf '%s\n' "$version_output" | grep -F "AlgoBox 1.1.1" >/dev/null

help_output="$("$exe" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Usage: algobox" >/dev/null

echo "algobox CLI smoke test passed"
