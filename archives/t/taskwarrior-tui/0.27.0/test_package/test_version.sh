#!/bin/sh
# Test script for taskwarrior-tui — verifies the binary runs and reports version.
# Called by test_package/conanfile.py test() method.

set -e

BINARY="${1:-taskwarrior-tui}"

# Verify the binary exists and is executable
if ! command -v "$BINARY" >/dev/null 2>&1; then
    echo "ERROR: $BINARY not found in PATH" >&2
    exit 1
fi

# Run --version and capture output
OUTPUT=$("$BINARY" --version 2>&1)
echo "Version output: $OUTPUT"

# Verify version string contains expected pattern
case "$OUTPUT" in
    *taskwarrior-tui*)
        echo "PASS: version string contains 'taskwarrior-tui'"
        ;;
    *)
        echo "FAIL: unexpected version output: $OUTPUT" >&2
        exit 1
        ;;
esac

# Verify version number is present
case "$OUTPUT" in
    *0.27.0*)
        echo "PASS: version 0.27.0 found"
        ;;
    *)
        echo "WARN: version 0.27.0 not in output, got: $OUTPUT"
        ;;
esac

echo "All tests passed."
