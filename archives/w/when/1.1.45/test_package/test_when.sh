#!/bin/bash
# test_when.sh — smoke test for when (Perl calendar tool)
# Verifies the installed 'when' binary responds to --version

set -e

OUTPUT=$(when --version 2>&1)
if echo "$OUTPUT" | grep -q "When version 1.1.45"; then
    echo "PASS: when --version returns correct version"
    exit 0
else
    echo "FAIL: when --version output unexpected: $OUTPUT"
    exit 1
fi
