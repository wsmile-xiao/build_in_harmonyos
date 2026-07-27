#!/bin/bash
# test.sh — lavat 3.0.0 smoke test
# Runs lavat -h and verifies the binary produces expected output.

set -euo pipefail

echo "=== lavat smoke test ==="

# Test 1: lavat -h should print usage
output=$(lavat -h 2>&1)
if echo "$output" | grep -q "Usage: lavat"; then
        echo "        [ok] lavat -h prints usage"
else
        echo "        [fail] lavat -h did not print expected usage"
        echo "$output"
        exit 1
fi

# Test 2: lavat -h should mention key options
if echo "$output" | grep -q "\-s <SPEED>"; then
        echo "        [ok] lavat -h mentions speed option"
else
        echo "        [fail] lavat -h did not mention speed option"
        exit 1
fi

echo "=== All tests passed ==="
