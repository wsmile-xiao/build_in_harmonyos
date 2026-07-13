#!/bin/sh
# R34: Test must actually exercise the tested package's binary
# batctl is a CLI tool — test by running batctl -v
set -e

BATCTL_BIN="${1:-batctl}"
output=$("$BATCTL_BIN" -v 2>&1)

# Verify the binary produces expected version output
case "$output" in
    *batctl*2025.2*)
        echo "PASS: batctl binary works correctly"
        echo "  output: $output"
        exit 0
        ;;
    *)
        echo "FAIL: unexpected output from batctl -v"
        echo "  output: $output"
        exit 1
        ;;
esac
