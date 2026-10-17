#!/bin/sh
# test.sh — iperf 2.2.1 test_package
# R34: This test executes the iperf binary from the package.
# Verifies that iperf --version returns the expected version string.

set -e

OUTPUT=$(iperf --version 2>&1)
echo "$OUTPUT"

# Verify the output contains the expected version
echo "$OUTPUT" | grep -q "iperf version 2.2.1"
if [ $? -eq 0 ]; then
    echo "TEST PASS: iperf --version returned expected version"
else
    echo "TEST FAIL: iperf --version did not return expected version"
    exit 1
fi
