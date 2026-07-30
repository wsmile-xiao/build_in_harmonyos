#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for lz4jsoncat executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] lz4jsoncat (no args, expect exit 0)"
lz4jsoncat && echo "✅ no-args exit 0 OK" || {
    echo "❌ lz4jsoncat failed with no args"
    exit 1
}
