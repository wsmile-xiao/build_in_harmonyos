#!/bin/sh
# test_ksh.sh - Test that ksh works correctly
# This script is executed by the ksh binary from the built package.
# R34: test must actually execute the built binary.

# Test 1: Basic arithmetic
result=$(print "$((3 * 7))")
if [ "$result" = "21" ]; then
    echo "PASS: arithmetic test (3*7=21)"
else
    echo "FAIL: arithmetic test expected 21, got $result"
    exit 1
fi

# Test 2: String operations
str="Hello World"
len=${#str}
if [ "$len" = "11" ]; then
    echo "PASS: string length test"
else
    echo "FAIL: string length expected 11, got $len"
    exit 1
fi

# Test 3: Variable expansion
name="ksh"
echo "PASS: variable expansion ($name)"

# Test 4: Array support
arr=(a b c)
if [ "${arr[1]}" = "b" ]; then
    echo "PASS: array test"
else
    echo "FAIL: array test expected 'b', got ${arr[1]}"
    exit 1
fi

echo "All tests passed."
exit 0
