#!/bin/sh
# test_lcdf_typetools.sh — L1 test source for lcdf-typetools
# Runs multiple tool --version checks to verify binaries are functional
set -e

CFFTOT1_BIN="${1:-cfftot1}"
OTFINFO_BIN="${2:-otfinfo}"
T1LINT_BIN="${3:-t1lint}"

# Test 1: cfftot1 --version
if ! "$CFFTOT1_BIN" --version >/dev/null 2>&1; then
    echo "FAIL: cfftot1 --version did not return success"
    exit 1
fi
OUTPUT=$("$CFFTOT1_BIN" --version 2>&1)
if echo "$OUTPUT" | grep -q "LCDF typetools"; then
    echo "PASS: cfftot1 --version returns correct version string"
else
    echo "FAIL: cfftot1 --version output does not contain 'LCDF typetools'"
    exit 1
fi

# Test 2: otfinfo --version
OUTPUT=$("$OTFINFO_BIN" --version 2>&1)
if echo "$OUTPUT" | grep -q "LCDF typetools"; then
    echo "PASS: otfinfo --version returns correct version string"
else
    echo "FAIL: otfinfo --version output does not contain 'LCDF typetools'"
    exit 1
fi

# Test 3: t1lint --version
OUTPUT=$("$T1LINT_BIN" --version 2>&1)
if echo "$OUTPUT" | grep -q "LCDF typetools"; then
    echo "PASS: t1lint --version returns correct version string"
else
    echo "FAIL: t1lint --version output does not contain 'LCDF typetools'"
    exit 1
fi

echo "All tests passed (3/3)"
exit 0
