#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for scsi-tgt executables
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] tgtd --version"
output=$(tgtd --version 2>&1 || true)
if echo "$output" | grep -q "1.0"; then
    echo "PASS: tgtd --version OK"
else
    echo "FAIL: tgtd --version failed: $output"
    exit 1
fi
