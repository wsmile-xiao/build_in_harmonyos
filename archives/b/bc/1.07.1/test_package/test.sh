#!/bin/bash
# Smoke test for bc and dc binaries
set -e

# Test bc --version
bc --version

# Test basic arithmetic
result=$(echo "2+3" | bc)
if [ "$result" != "5" ]; then
    echo "FAIL: bc 2+3 expected 5, got $result"
    exit 1
fi

# Test multiplication
result=$(echo "4*5" | bc)
if [ "$result" != "20" ]; then
    echo "FAIL: bc 4*5 expected 20, got $result"
    exit 1
fi

# Test dc (desk calculator)
result=$(echo "2 3 + p" | dc)
if [ "$result" != "5" ]; then
    echo "FAIL: dc 2 3 + p expected 5, got $result"
    exit 1
fi

echo "All tests passed"
