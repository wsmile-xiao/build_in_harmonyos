#!/bin/sh
# test_package/test_flow.sh
# L1 test: verify the flow-cli binary is correctly packaged.
# Uses ELF header verification (od hexdump) instead of binary execution
# because the OHOS CI worker's HMDFS at the Conan cache path does not
# support the execute permission bit (E046: chmod() ineffective on OHOS).
# Per P013: platform limitations must be downgraded to available solutions.

set -e

FLOW_BIN="${1:-flow-cli}"

# Verify binary exists
if ! FLOW_BIN=$(command -v "$FLOW_BIN" 2>/dev/null); then
    echo "FAIL: flow-cli not found in PATH"
    exit 1
fi

# Check ELF magic bytes (7f 45 4c 46 = \x7fELF)
# Uses od (octal dump) which is widely available on OHOS and Linux
ELF_MAGIC=$(od -An -tx1 -N4 "$FLOW_BIN" 2>/dev/null | tr -d ' \n')
if [ "$ELF_MAGIC" = "7f454c46" ]; then
    echo "PASS: ELF binary detected at $(command -v "$FLOW_BIN")"
    # Show file size
    FILE_SIZE=$(wc -c < "$FLOW_BIN" 2>/dev/null || stat -c%s "$FLOW_BIN" 2>/dev/null || echo "?")
    echo "Binary size: $FILE_SIZE bytes"
else
    echo "FAIL: $FLOW_BIN is not a valid ELF binary (magic=$ELF_MAGIC)"
    exit 1
fi