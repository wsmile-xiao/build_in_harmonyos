#!/bin/bash
# test_package/test.sh — smoke test for abcselect
set -euo pipefail

echo "[test] abcselect -?"
perl "$(command -v abcselect)" -? 2>&1 || {
    echo "❌ abcselect -? failed"
    exit 1
}
echo "✅ abcselect -? OK"
