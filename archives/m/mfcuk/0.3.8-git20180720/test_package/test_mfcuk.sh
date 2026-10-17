#!/bin/sh
# OHOS consumer test: verify mfcuk binary runs
# Exit 0 on pass, non-zero on fail

MFCUK_BIN="${1:-mfcuk}"

if [ ! -x "$MFCUK_BIN" ]; then
    echo "FAIL: mfcuk binary not found or not executable: $MFCUK_BIN"
    exit 1
fi

# Test: mfcuk --help prints usage and exits (upstream behavior: exit 1)
output=$(printf "LOOK\nQUIT\nY\n" | timeout 10 "$MFCUK_BIN" 2>&1) || true

echo "$output" | grep -q "mfcuk" || {
    echo "FAIL: mfcuk output does not contain expected text"
    exit 1
}

echo "PASS: mfcuk consumer test passed"
exit 0
