#!/bin/sh
# test_package smoke test for openfortivpn
# Executes the binary with --version and verifies output
set -eu

BIN="$1"
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "FAIL: binary not found or not executable: $BIN"
    exit 1
fi
VERSION_OUTPUT=$("$BIN" --version 2>&1)
echo "Version output: $VERSION_OUTPUT"
case "$VERSION_OUTPUT" in
    *1.24.1*)
        echo "PASS: openfortivpn --version returns 1.24.1"
        exit 0
        ;;
    *)
        echo "FAIL: openfortivpn --version did not return expected version"
        exit 1
        ;;
esac
