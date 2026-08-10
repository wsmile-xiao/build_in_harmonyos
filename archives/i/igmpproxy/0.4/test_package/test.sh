#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the igmpproxy executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] igmpproxy -h (help/version)"
OUTPUT=$(igmpproxy -h 2>&1 || true)
echo "$OUTPUT" | head -5

if ! echo "$OUTPUT" | grep -q "igmpproxy 0.4"; then
    echo "FAIL: igmpproxy -h did not output version string"
    exit 1
fi
echo "OK: igmpproxy binary runs and reports version 0.4"
