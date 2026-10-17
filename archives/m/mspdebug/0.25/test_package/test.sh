#!/bin/sh
# test_package/test.sh — consumer test for the mspdebug binary.
# Runs in conanrun env (resolves the packaged libusb-compat/libusb
# dependencies at runtime).
set -eu

echo "[test] mspdebug --version"
out=$(mspdebug --version)
echo "$out" | grep -q "MSPDebug version 0.25"
echo "OK: mspdebug --version reports 0.25 (exit 0)"

echo "ALL CONSUMER TESTS PASSED"
