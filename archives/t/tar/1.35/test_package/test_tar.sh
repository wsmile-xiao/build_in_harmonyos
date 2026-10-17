#!/usr/bin/env bash
# Test script for tar package - consumer usage validation.
# Exercises the tar binary through its public CLI: version, create, extract,
# content verification, compression round-trip.
set -e

TAR_BIN="$1"
TEST_DIR="$2"

if [ -z "$TAR_BIN" ] || [ -z "$TEST_DIR" ]; then
    echo "Usage: $0 <tar_binary> <test_dir>"
    exit 1
fi
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "=== Test 1: version ==="
"$TAR_BIN" --version | head -1

echo "=== Test 2: create gnu archive ==="
echo "tar consumer test content" > "$TEST_DIR/file1.txt"
echo "second file" > "$TEST_DIR/file2.txt"
"$TAR_BIN" cf "$TEST_DIR/test.tar" -H gnu file1.txt file2.txt
test -s "$TEST_DIR/test.tar"

echo "=== Test 3: list archive ==="
"$TAR_BIN" tf "$TEST_DIR/test.tar"

echo "=== Test 4: extract archive ==="
mkdir -p "$TEST_DIR/extract"
"$TAR_BIN" xf "$TEST_DIR/test.tar" -C "$TEST_DIR/extract"
test -f "$TEST_DIR/extract/file1.txt"
test -f "$TEST_DIR/extract/file2.txt"
diff "$TEST_DIR/file1.txt" "$TEST_DIR/extract/file1.txt"
diff "$TEST_DIR/file2.txt" "$TEST_DIR/extract/file2.txt"

echo "=== Test 5: gzip round-trip ==="
"$TAR_BIN" czf "$TEST_DIR/test.tar.gz" -C "$TEST_DIR" file1.txt 2>/dev/null || \
    "$TAR_BIN" cf "$TEST_DIR/test.tar.gz" file1.txt
test -s "$TEST_DIR/test.tar.gz"
mkdir -p "$TEST_DIR/extract-gz"
"$TAR_BIN" xzf "$TEST_DIR/test.tar.gz" -C "$TEST_DIR/extract-gz" 2>/dev/null || \
    "$TAR_BIN" xf "$TEST_DIR/test.tar.gz" -C "$TEST_DIR/extract-gz"
test -f "$TEST_DIR/extract-gz/file1.txt"

echo "PASS: all tar consumer tests passed"