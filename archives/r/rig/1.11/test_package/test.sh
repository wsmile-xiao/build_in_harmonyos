#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for rig executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# Find data directory relative to the rig binary
rig_bin=$(command -v rig || echo "")
if [ -z "$rig_bin" ]; then
    echo "❌ rig binary not found in PATH"
    exit 1
fi
pkg_root=$(dirname "$(dirname "$rig_bin")")
datadir="$pkg_root/share/rig"

echo "[test] rig -c 1 (datadir=$datadir)"
output=$(rig -d "$datadir" -c 1 2>&1)
if [ -n "$output" ]; then
    echo "✅ rig -c 1 produced output"
    echo "$output" | head -4
else
    echo "❌ rig -c 1 produced no output"
    exit 1
fi

echo "[test] rig -f -c 1"
output=$(rig -d "$datadir" -f -c 1 2>&1)
if [ -n "$output" ]; then
    echo "✅ rig -f -c 1 produced output"
else
    echo "❌ rig -f -c 1 failed"
    exit 1
fi

echo "[test] rig -m -c 1"
output=$(rig -d "$datadir" -m -c 1 2>&1)
if [ -n "$output" ]; then
    echo "✅ rig -m -c 1 produced output"
else
    echo "❌ rig -m -c 1 failed"
    exit 1
fi

echo "All tests passed."
