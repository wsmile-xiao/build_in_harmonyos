#!/bin/bash
# test_package/test.sh — L1 smoke test for ocrad
# R34: executes the actual ocrad binary.
set -e

# Find the ocrad binary
OCRAD=""
# Method 1: PATH (set by VirtualRunEnv)
OCRAD=$(command -v ocrad 2>/dev/null || echo "")

# Method 2: Search common conan package locations
if [ -z "$OCRAD" ]; then
    for d in \
        "$(dirname "$0")/../../bin" \
        "$(dirname "$0")/../../../bin" \
        "${HOME}/.conan2/p"/*/p/bin \
        /storage/*/conan2/p/*/p/bin; do
        if [ -f "$d/ocrad" ]; then
            OCRAD="$d/ocrad"
            break
        fi
    done
fi

if [ -z "$OCRAD" ]; then
    echo "ERROR: ocrad binary not found"
    echo "PATH=$PATH"
    find / -name ocrad -type f 2>/dev/null | head -5
    exit 1
fi

echo "Found ocrad at: $OCRAD"

# Ensure it's executable
chmod +x "$OCRAD" 2>/dev/null || true

# Run ocrad --version to verify the binary works
echo "Running: ocrad --version"
$OCRAD --version
echo "ocrad --version exit code: $?"

# Verify version output contains "0.29"
if $OCRAD --version 2>&1 | grep -q "0.29"; then
    echo "PASS: ocrad version 0.29 confirmed"
else
    echo "FAIL: ocrad version mismatch"
    exit 1
fi

echo "All tests passed."
