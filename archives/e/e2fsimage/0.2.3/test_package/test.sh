#!/bin/sh
# test.sh — smoke test for e2fsimage binary
# R34: test must genuinely depend on the e2fsimage package.
# If the binary is removed (L1e destructive test), this test will fail.

# Check if e2fsimage is available in PATH (via VirtualRunEnv)
if ! command -v e2fsimage >/dev/null 2>&1; then
    echo "FAIL: e2fsimage binary not found in PATH"
    exit 1
fi

# Run e2fsimage with no args - should print usage and exit non-zero
output=$(e2fsimage 2>&1) || true

if echo "$output" | grep -qi "usage\|e2fsimage\|source.*directory"; then
    echo "PASS: e2fsimage binary is installed and produces expected output"
    exit 0
else
    echo "FAIL: unexpected output from e2fsimage"
    echo "Output: $output"
    exit 1
fi
