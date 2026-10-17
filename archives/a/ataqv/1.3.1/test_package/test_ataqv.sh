#!/bin/sh
# test_package/test_ataqv.sh — smoke test for ataqv CLI binary (R34)
set -u

# 1. Check binary exists
ataqv_bin="${1:-}"
if [ -z "$ataqv_bin" ]; then
    echo "FAIL: ataqv binary path not provided" >&2
    exit 1
fi
if [ ! -x "$ataqv_bin" ]; then
    echo "FAIL: ataqv binary not found or not executable: $ataqv_bin" >&2
    exit 1
fi
echo "OK: ataqv binary found at $ataqv_bin"

# 2. Run --version and verify output
version_output=$("$ataqv_bin" --version 2>&1) || true
echo "$version_output" | grep -q "1.3.1"
if [ $? -eq 0 ]; then
    echo "PASS: ataqv --version output contains 1.3.1"
else
    echo "FAIL: ataqv --version output does not contain 1.3.1: $version_output" >&2
    exit 1
fi
