#!/bin/sh
# Smoke test for blind — verify blind-arithm binary runs and shows usage
set -euo pipefail

BLIND_BIN="${1:-blind-arithm}"

# Run blind-arithm without arguments, expect usage output
output=$("$BLIND_BIN" 2>&1) || true

# Verify it outputs usage information (not silent crash)
if echo "$output" | grep -q "usage"; then
    echo "PASS: blind-arithm shows usage information"
    exit 0
else
    echo "FAIL: blind-arithm did not show expected usage output"
    echo "Output: $output"
    exit 1
fi
