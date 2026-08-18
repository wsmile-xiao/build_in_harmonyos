#!/bin/bash
# test_ems_flasher.sh — Test source file for ems-flasher test_package.
# This is a test source file required by CI L0c (no_test_sources gate).
# The actual test logic is in conanfile.py test() method, which executes
# the ems-flasher binary directly with --version.
#
# This script can also be run standalone to verify the binary:
#   ./test_ems_flasher.sh /path/to/ems-flasher

# R25: strict shell mode
set -euo pipefail

BIN="${1:-ems-flasher}"

# R34: Execute the ems-flasher binary to verify it runs and links correctly.
# Wrapped in `if` so a non-zero exit is captured for reporting instead of
# being aborted by `set -e`.
if output=$("$BIN" --version 2>&1); then
    rc=0
else
    rc=$?
fi

if [ "$rc" -ne 0 ]; then
    echo "FAIL: ems-flasher --version exited with $rc"
    echo "Output: $output"
    exit 1
fi

# Verify output contains "EMS-flasher"
if echo "$output" | grep -q "EMS-flasher"; then
    echo "PASS: ems-flasher --version output correct: $output"
    exit 0
else
    echo "FAIL: ems-flasher --version output unexpected: $output"
    exit 1
fi
