#!/usr/bin/env bash
# test_iperf3.sh — Conan L1 test for iperf3 3.18
# Runs iperf3 --version and checks output contains expected version string.
set -euo pipefail

IPERF3_BIN="$1"

if [ -z "$IPERF3_BIN" ]; then
    echo "ERROR: iperf3 binary path not provided"
    exit 1
fi

if [ ! -f "$IPERF3_BIN" ]; then
    echo "ERROR: iperf3 binary not found at $IPERF3_BIN"
    exit 1
fi

# Run iperf3 --version and capture output
output=$("$IPERF3_BIN" --version 2>&1)

# Check that version string is present
if echo "$output" | grep -q "iperf.*3.18"; then
    echo "PASS: iperf3 --version output contains version 3.18"
    echo "$output" | head -3
    exit 0
else
    echo "FAIL: iperf3 --version output does not contain expected version"
    echo "$output"
    exit 1
fi
