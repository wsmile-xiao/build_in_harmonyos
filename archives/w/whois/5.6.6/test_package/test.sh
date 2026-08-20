#!/usr/bin/env bash
# test.sh — whois 5.6.6 smoke test
# R34: Exercise the actual whois binary
set -euo pipefail

WHOIS_BIN="${WHOIS_BIN:-whois}"

output=$("$WHOIS_BIN" --version 2>&1)
echo "$output"

if echo "$output" | grep -q "Version 5.6.6"; then
    echo "PASS: whois --version output verified"
    exit 0
else
    echo "FAIL: expected 'Version 5.6.6' in output"
    exit 1
fi
