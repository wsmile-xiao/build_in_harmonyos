#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ipv6toolkit addr6 binary
# Runs in conanrun env (PATH includes installed bin/).
# Exercises real addr6 address parsing (R34), not just a string-printing stub.
set -euo pipefail

echo "[test] addr6 -a ::1 -q"
out=$(addr6 -a ::1 -q)
if [ "$out" = "::1" ]; then
    echo "PASS: addr6 -a ::1 -q -> ::1"
else
    echo "FAIL: addr6 -a ::1 -q -> '$out' (expected '::1')"
    exit 1
fi

echo "[test] addr6 -a fe80::1 -q"
out=$(addr6 -a fe80::1 -q)
if [ "$out" = "fe80::1" ]; then
    echo "PASS: addr6 -a fe80::1 -q -> fe80::1"
else
    echo "FAIL: addr6 -a fe80::1 -q -> '$out' (expected 'fe80::1')"
    exit 1
fi

echo "[test] addr6 -a ff02::1 -q"
out=$(addr6 -a ff02::1 -q)
if [ "$out" = "ff02::1" ]; then
    echo "PASS: addr6 -a ff02::1 -q -> ff02::1"
else
    echo "FAIL: addr6 -a ff02::1 -q -> '$out' (expected 'ff02::1')"
    exit 1
fi

echo ""
echo "All ipv6toolkit smoke tests passed."
