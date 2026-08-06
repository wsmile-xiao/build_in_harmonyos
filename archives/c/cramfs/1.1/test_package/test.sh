#!/bin/sh
# Test cramfs tools: create a cramfs image with mkcramfs and verify with cramfsck
set -euo pipefail

TMPDIR=$(mktemp -d)
echo "hello cramfs" > "$TMPDIR/hello.txt"
mkdir -p "$TMPDIR/subdir"
echo "nested file" > "$TMPDIR/subdir/nested.txt"

# Create a cramfs image
mkcramfs "$TMPDIR" "$TMPDIR/test.img"

# Verify the image
cramfsck "$TMPDIR/test.img"

# Cleanup
rm -rf "$TMPDIR"

echo "cramfs test: OK"
