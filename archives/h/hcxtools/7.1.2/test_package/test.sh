#!/bin/sh
# test.sh — Consumer smoke test for hcxtools
# Runs the installed hcxpcapngtool binary and verifies version output.
# R34: test exercises the packaged binary, not a static string.

set -e

BIN="${1:-hcxpcapngtool}"

output=$("$BIN" --version 2>&1) || {
    echo "FAIL: $BIN --version exited with code $?"
    exit 1
}

case "$output" in
    *7.1.2*)
        echo "PASS: $BIN reports version 7.1.2"
        ;;
    *)
        echo "FAIL: $BIN version output unexpected: $output"
        exit 1
        ;;
esac

# Also verify another tool
hcxpsktool --version 2>&1 | grep -q "7.1.2" && echo "PASS: hcxpsktool version OK" || {
    echo "FAIL: hcxpsktool version check failed"
    exit 1
}

echo "All smoke tests passed."
