#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for disktype executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] disktype smoke test"
# disktype does not support --version; running without args shows Usage
disktype > /dev/null 2>&1 && {
    echo "❌ disktype should exit non-zero without arguments"
    exit 1
} || echo "✅ disktype correctly exits non-zero without args"

# Test with an empty file
tmpfile=$(mktemp)
: > "$tmpfile"
disktype "$tmpfile" 2>&1 | grep -q "Regular file" && echo "✅ empty file detection OK" || {
    echo "❌ empty file detection failed"
    rm -f "$tmpfile"
    exit 1
}
rm -f "$tmpfile"
echo "✅ All smoke tests passed"
