#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for goenv executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "[fail] usage: $0 <path-to-goenv>" >&2
    exit 2
fi

goenv_bin="$1"

if [ ! -f "$goenv_bin" ]; then
    echo "[fail] goenv binary not found: $goenv_bin" >&2
    exit 1
fi

# goenv --version outputs: "goenv 3.1.1"
version_output="$("$goenv_bin" --version)"
printf '%s\n' "$version_output" | grep -F "goenv" >/dev/null
printf '%s\n' "$version_output" | grep -F "3.1.1" >/dev/null
echo "[ok] goenv --version OK"
