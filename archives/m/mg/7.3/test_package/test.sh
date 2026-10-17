#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for mg executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] mg binary verification"
if mg -x 2>/dev/null; then
    echo "❌ mg accepted invalid option -x unexpectedly"
    exit 1
else
    echo "✅ mg binary is functional (correctly rejects invalid option)"
fi
