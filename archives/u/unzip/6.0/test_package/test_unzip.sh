#!/bin/sh
# test_unzip.sh — Test script for unzip binary (R34: substantial dependency on tested package)
# Usage: test_unzip.sh <unzip_binary> <test_zip> <extract_dir>
set -e

UNZIP_BIN="$1"
TEST_ZIP="$2"
EXTRACT_DIR="$3"

# Run unzip to extract the archive
"$UNZIP_BIN" -o "$TEST_ZIP" -d "$EXTRACT_DIR"

# Verify extracted content
EXTRACTED_FILE="$EXTRACT_DIR/hello.txt"
if [ ! -f "$EXTRACTED_FILE" ]; then
    echo "FAIL: Expected file $EXTRACTED_FILE not found after unzip"
    exit 1
fi

EXPECTED="Hello from unzip test!"
ACTUAL=$(cat "$EXTRACTED_FILE")
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "FAIL: Content mismatch: expected '$EXPECTED', got '$ACTUAL'"
    exit 1
fi

echo "PASS: unzip successfully extracted and verified hello.txt"
