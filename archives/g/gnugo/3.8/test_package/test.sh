#!/bin/sh
# Test script for gnugo 3.8 - verify the binary works
# This script is called by test_package/conanfile.py test() method

set -e

# Get the gnugo binary path from the first argument
GNUGO_BIN="${1:-gnugo}"

# Run gnugo --version and verify output
OUTPUT=$("$GNUGO_BIN" --version 2>&1)

# Check that output contains "GNU Go"
echo "$OUTPUT" | grep -q "GNU Go"
if [ $? -eq 0 ]; then
    echo "TEST PASSED: gnugo --version output contains 'GNU Go'"
    echo "Version output: $OUTPUT"
    exit 0
else
    echo "TEST FAILED: gnugo --version does not contain 'GNU Go'"
    echo "Actual output: $OUTPUT"
    exit 1
fi
