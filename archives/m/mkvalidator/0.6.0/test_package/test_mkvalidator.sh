#!/bin/sh
# R34: Test must actually exercise the tested package's binary
# mkvalidator is a CLI tool — test by running mkvalidator --version
set -e

MKVALIDATOR_BIN="${1:-mkvalidator}"
output=$("$MKVALIDATOR_BIN" --version 2>&1)

# Verify the binary produces expected version output
case "$output" in
    *mkvalidator*0.6.0*)
        echo "PASS: mkvalidator binary works correctly"
        echo "  output: $output"
        exit 0
        ;;
    *)
        echo "FAIL: unexpected output from mkvalidator --version"
        echo "  output: $output"
        exit 1
        ;;
esac
