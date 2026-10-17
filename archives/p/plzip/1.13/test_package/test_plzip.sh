#!/system/bin/sh
# test_plzip.sh — Compression/decompression roundtrip test for plzip
# Called by test_package/conanfile.py test() method
#
# This script:
# 1. Creates a test input file with known content
# 2. Compresses it with plzip
# 3. Decompresses the compressed file to a different output
# 4. Compares the output with the original (using cmp)
# 5. Exits 0 on success, 1 on failure

set -e

PLZIP_BIN="$1"
TEST_DIR="${2:-.}"

INPUT="$TEST_DIR/test_input.txt"
COMPRESSED="$TEST_DIR/test_input.txt.lz"
OUTPUT="$TEST_DIR/test_output.txt"

# Clean up any leftover files
rm -f "$INPUT" "$COMPRESSED" "$OUTPUT"

# Create a test input file
cat > "$INPUT" << 'HEREDOC'
The quick brown fox jumps over the lazy dog.
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
HEREDOC

# Compress (creates .lz, keeps original with -k)
"$PLZIP_BIN" -k -f "$INPUT"

# Verify compressed file exists
if [ ! -f "$COMPRESSED" ]; then
    rm -f "$INPUT"
    exit 1
fi

# Decompress to a specific output file
"$PLZIP_BIN" -d -k -f -o "$OUTPUT" "$COMPRESSED"

# Verify output file exists
if [ ! -f "$OUTPUT" ]; then
    rm -f "$INPUT" "$COMPRESSED"
    exit 1
fi

# Compare original and decompressed content
if cmp -s "$INPUT" "$OUTPUT"; then
    # Clean up
    rm -f "$INPUT" "$COMPRESSED" "$OUTPUT"
    exit 0
else
    rm -f "$INPUT" "$COMPRESSED" "$OUTPUT"
    exit 1
fi
