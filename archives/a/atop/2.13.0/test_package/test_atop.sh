#!/system/bin/sh
# test_atop.sh — Smoke test for atop binary
# Runs atop -V to verify the binary is functional
# Usage: test_atop.sh <path_to_atop_binary>
set -e

ATOP_BIN="$1"
if [ -z "$ATOP_BIN" ]; then
    echo "ERROR: No atop binary path provided"
    exit 1
fi

if [ ! -x "$ATOP_BIN" ]; then
    echo "ERROR: atop binary not found or not executable: $ATOP_BIN"
    exit 1
fi

echo "Testing atop binary: $ATOP_BIN"
OUTPUT=$("$ATOP_BIN" -V 2>&1)
echo "atop -V output: $OUTPUT"

# Verify the version string contains "Version:" and "2.13"
if echo "$OUTPUT" | grep -q "Version:" && echo "$OUTPUT" | grep -q "2.13"; then
    echo "PASS: atop -V returned valid version"
    exit 0
else
    echo "FAIL: atop -V did not return expected version string"
    exit 1
fi
