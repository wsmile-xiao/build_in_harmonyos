#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cidrmerge executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] cidrmerge -v"
cidrmerge -v && echo "✅ -v OK" || {
    echo "❌ cidrmerge -v failed"
    exit 1
}

echo "[test] CIDR merge functionality"
output=$(echo -e "10.1.1.0/24\n10.1.1.1/32\n192.1.4.5/32\n192.1.4.4/32" | cidrmerge)
expected="10.1.1.0/24
192.1.4.4/31"
if [ "$output" = "$expected" ]; then
    echo "✅ CIDR merge OK"
else
    echo "❌ CIDR merge failed: expected '$expected', got '$output'"
    exit 1
fi

echo "[test] empty input"
echo -n "" | cidrmerge && echo "✅ empty input OK" || {
    echo "❌ empty input failed"
    exit 1
}

echo "All tests passed."
