#!/bin/sh
# test_package test script for jo 1.9
# Verifies jo binary produces correct JSON output
set -e

JO_BIN="${JO:-jo}"

# Test 1: version check
v=$("$JO_BIN" -v)
[ "$v" = "jo 1.9" ] || { echo "FAIL: version mismatch: $v"; exit 1; }

# Test 2: JSON object generation
out=$("$JO_BIN" name=John age=30)
[ "$out" = '{"name":"John","age":30}' ] || { echo "FAIL: object: $out"; exit 1; }

# Test 3: JSON array generation
out=$("$JO_BIN" -a apple banana cherry)
[ "$out" = '["apple","banana","cherry"]' ] || { echo "FAIL: array: $out"; exit 1; }

echo "All jo tests passed"
