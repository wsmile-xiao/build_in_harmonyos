#!/usr/bin/env bash
# test_package/test.sh — smoke test for asn CLI tool
# Verifies the asn script is installed, syntactically valid, and functional.
set -euo pipefail

echo "[test] asn script exists"
if command -v asn >/dev/null 2>&1; then
    echo "✅ asn found in PATH"
else
    echo "❌ asn not found in PATH"
    exit 1
fi

echo "[test] asn syntax check"
asn_file="$(command -v asn)"
if bash -n "$asn_file"; then
    echo "✅ asn syntax OK"
else
    echo "❌ asn syntax check failed"
    exit 1
fi

echo "[test] asn version string"
if grep -q 'ASN_VERSION="0.81.0"' "$asn_file"; then
    echo "✅ ASN_VERSION=0.81.0 verified"
else
    echo "❌ ASN_VERSION string not found"
    exit 1
fi

echo "[test] asn usage output"
# Run asn without arguments — should produce usage output
# Capture both stdout and stderr; asn may exit non-zero when showing usage
asn_output=$(asn 2>&1) || true
if echo "$asn_output" | grep -qi -e "ASN" -e "usage" -e "IPv4" -e "IPv6"; then
    echo "✅ asn usage output OK"
else
    echo "❌ asn produced no recognizable output"
    exit 1
fi

echo ""
echo "All asn smoke tests passed."
