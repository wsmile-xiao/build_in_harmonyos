#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for calc executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] calc version"
output=$(calc -v 2>&1 || true)
if echo "$output" | grep -qi "version 3.0.1.0"; then
    echo "✅ calc -v version OK"
else
    echo "❌ calc -v version check failed (got: $output)"
    exit 1
fi

echo "[test] calc evaluates simple expression"
output=$(echo "2+3" | calc -q 2>&1 || true)
if echo "$output" | grep -qE "^\s*5\s*$"; then
    echo "✅ calc 2+3 = 5 OK"
else
    echo "❌ calc 2+3 failed (got: $output)"
    exit 1
fi

echo "[test] calc arbitrary precision"
output=$(echo "12345678901234567890*98765432109876543210" | calc -q 2>&1 || true)
if echo "$output" | grep -q "1219326311370217952237463801111263526900"; then
    echo "✅ calc big integer multiplication OK"
else
    echo "❌ calc big integer multiplication failed (got: $output)"
    exit 1
fi

echo "[test] calc generic file position tracking (test_fpos.cal)"
fpos_dir=$(dirname "$0")
output=$(calc -q -f "$fpos_dir/test_fpos.cal" 2>&1 || true)
echo "$output" | grep -q "TEST_FPOS_PASSED" && echo "$output" | grep -q "FAIL 0"
if [ $? -eq 0 ]; then
    echo "✅ test_fpos.cal file position tracking OK"
else
    echo "❌ test_fpos.cal failed (got: $output)"
    exit 1
fi