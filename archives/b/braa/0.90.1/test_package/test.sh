#!/data/service/hnp/bin/bash
# test_package/test.sh — behavioral tests for the braa executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

echo "[test] braa -h prints version banner and usage"
braa -h > "$OUT/braa_help.txt"
grep -q "braa 0.90.1" "$OUT/braa_help.txt"
grep -q "usage: braa" "$OUT/braa_help.txt"
echo "OK: -h shows braa 0.90.1 banner and usage"

echo "[test] braa -r 0 rejects an invalid retry count"
if braa -r 0 2> "$OUT/braa_err.txt"; then
    echo "FAIL: braa -r 0 should exit non-zero"
    exit 1
fi
grep -q "Invalid retry count" "$OUT/braa_err.txt"
echo "OK: -r 0 rejected with 'Invalid retry count.'"

echo "[test] braa issues a real SNMP GET over UDP to 127.0.0.1"
braa -v -a 5 -t 2 -r 1 127.0.0.1:.1.3.6.1.2.1.1.1.0 > "$OUT/braa_snmp.txt"
cat "$OUT/braa_snmp.txt"
grep -q "1 queries made" "$OUT/braa_snmp.txt"
grep -q "0 queries acknowledged" "$OUT/braa_snmp.txt"
echo "OK: SNMP GET exercised the built-in UDP/SNMP stack (no local agent, 0 acknowledged)"
