#!/system/bin/sh
# test_grepcidr.sh — functional test for grepcidr binary
# Usage: sh test_grepcidr.sh /path/to/grepcidr

set -u

GREPCIDR="$1"

if [ -z "$GREPCIDR" ] || [ ! -x "$GREPCIDR" ]; then
    echo "ERROR: grepcidr binary not found or not executable: $GREPCIDR"
    exit 1
fi

# Test 1: Version output (grepcidr -V returns exit code 2 by design)
"$GREPCIDR" -V 2>&1 | grep "grepcidr 2.0" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: grepcidr -V did not show expected version"
    exit 1
fi

# Test 2: CIDR matching — 192.168.1.1 should match 192.168.0.0/16
printf "192.168.1.1\n10.0.0.1\n" | "$GREPCIDR" 192.168.0.0/16 | grep "192.168.1.1" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: grepcidr did not match expected IP in CIDR range"
    exit 1
fi

# Test 3: Non-matching — 10.0.0.1 should NOT match 192.168.0.0/16
printf "10.0.0.1\n" | "$GREPCIDR" 192.168.0.0/16 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "FAIL: grepcidr matched non-matching IP (should not have)"
    exit 1
fi

echo "PASS: all grepcidr tests passed"
exit 0
