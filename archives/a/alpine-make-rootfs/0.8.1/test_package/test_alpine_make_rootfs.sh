#!/bin/bash
# Verify the packaged alpine-make-rootfs script.

set -euo pipefail

ROOTFS_BIN="${1:-}"
TEST_SHELL="${2:-}"

if [ -z "$ROOTFS_BIN" ] || [ -z "$TEST_SHELL" ]; then
    echo "ERROR: alpine-make-rootfs binary path and shell path are required"
    exit 1
fi

if [ ! -x "$ROOTFS_BIN" ]; then
    echo "ERROR: $ROOTFS_BIN not found or not executable"
    exit 1
fi

if [ ! -x "$TEST_SHELL" ]; then
    echo "ERROR: $TEST_SHELL not found or not executable"
    exit 1
fi

# Test --version output
version_output="$("$TEST_SHELL" "$ROOTFS_BIN" --version)"
printf "%s\n" "$version_output" | grep -F "0.8.1"

# Test --help output
help_output="$("$TEST_SHELL" "$ROOTFS_BIN" --help)"
printf "%s\n" "$help_output" | grep -F "Usage:"
printf "%s\n" "$help_output" | grep -F -- "--packages"

echo "PASS: alpine-make-rootfs --version and --help output are valid"
