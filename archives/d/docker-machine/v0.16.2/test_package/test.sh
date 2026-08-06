#!/bin/bash
set -euo pipefail

# R34: Test must exercise the actual docker-machine binary
BINARY="$(which docker-machine 2>/dev/null || echo docker-machine)"
echo "Testing: $BINARY"

# Run version check — validates the binary is executable and functional
VERSION_OUTPUT="$($BINARY version 2>&1)"
echo "Output: $VERSION_OUTPUT"

# Assert version string is present
if echo "$VERSION_OUTPUT" | grep -q "0.16.2"; then
    echo "PASS: docker-machine version 0.16.2 verified"
else
    echo "FAIL: version string not found"
    exit 1
fi
