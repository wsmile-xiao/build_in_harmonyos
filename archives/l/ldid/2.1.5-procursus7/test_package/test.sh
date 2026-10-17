#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ldid executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] ldid --version"
OUTPUT=$(ldid --version 2>&1) || true
echo "$OUTPUT" | head -1
echo "$OUTPUT" | grep -q "Link Identity Editor" || {
    echo "FAIL: --version does not contain 'Link Identity Editor'"
    exit 1
}
echo "OK: --version outputs 'Link Identity Editor'"

echo "[test] ldid --version shows usage"
echo "$OUTPUT" | grep -q "Usage" || {
    echo "FAIL: --version does not show Usage"
    exit 1
}
echo "OK: --version shows Usage information"
