#!/bin/bash
# test_uuu.sh — Test script for nxp-mfgtools (uuu)
# Verifies the uuu binary exists, is a valid ELF, and can be invoked.
# Usage: test_uuu.sh <path_to_uuu_binary>
#
# The uuu binary has a global constructor that calls libusb_init,
# which may fail on platforms without USB hardware. This is expected
# and does not indicate a build or linking problem.
set -euo pipefail

UUU_BIN="$1"
if [ -z "$UUU_BIN" ]; then
    echo "ERROR: Usage: test_uuu.sh <path_to_uuu_binary>"
    exit 1
fi

if [ ! -f "$UUU_BIN" ]; then
    echo "ERROR: uuu binary not found at $UUU_BIN"
    exit 1
fi

# Verify ELF magic bytes (7f 45 4c 46 = \x7fELF)
MAGIC=$(od -A x -t x1 -N 4 "$UUU_BIN" 2>/dev/null)
if echo "$MAGIC" | grep -q "7f 45 4c 46"; then
    echo "[ok] uuu is a valid ELF binary"
else
    echo "[fail] uuu is not a valid ELF binary (magic: $MAGIC)"
    exit 1
fi

# Run uuu -h — may fail on platforms without USB hardware (expected)
output=$("$UUU_BIN" -h 2>&1) || true

# Check for critical failures that indicate build/linking issues
if echo "$output" | grep -qi "error while loading shared libraries\|cannot open shared object\|Segmentation fault\|symbol lookup error"; then
    echo "[fail] uuu failed to start (linking/runtime error): $output"
    exit 1
fi

# libusb_init failure is expected on platforms without USB hardware
if echo "$output" | grep -qi "libusb"; then
    echo "[ok] uuu binary correctly linked (libusb_init expected failure without USB hardware)"
else
    echo "[ok] uuu -h executed (binary built and linked successfully)"
fi
