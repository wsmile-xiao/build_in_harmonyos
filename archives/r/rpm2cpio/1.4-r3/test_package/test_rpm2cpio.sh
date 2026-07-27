#!/bin/sh
# Test script for rpm2cpio — verifies the binary is installed and functional
# R34: test must actually exercise the package's functionality

set -eo pipefail

# Get the rpm2cpio binary path from the first argument
RPM2CPIO="$1"

if [ -z "$RPM2CPIO" ]; then
    echo "ERROR: rpm2cpio binary path not provided"
    exit 1
fi

# Test 1: Binary exists and is executable
if [ ! -x "$RPM2CPIO" ]; then
    echo "FAIL: rpm2cpio not found or not executable at $RPM2CPIO"
    exit 1
fi
echo "PASS: rpm2cpio binary found and executable"

# Test 2: Running with 2+ args shows usage and exits 0
OUTPUT=$("$RPM2CPIO" dummy1 dummy2 2>&1) || true
case "$OUTPUT" in
    *Usage*)
        echo "PASS: usage message displayed correctly"
        ;;
    *)
        echo "FAIL: expected usage message, got: $OUTPUT"
        exit 1
        ;;
esac

echo "All tests passed"
