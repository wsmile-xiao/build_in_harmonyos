#!/bin/sh
# test_lzip.sh — lzip compression/decompression roundtrip test
# Called by test_package/conanfile.py test() method
set -eu

# Clean up any leftover files
rm -f test_input.txt test_input.txt.lz test_output.txt

# Create test input
i=1
while [ $i -le 100 ]; do
  echo "Hello lzip! Compression roundtrip test."
  i=$((i + 1))
done > test_input.txt

# Compress (keep original with -k)
lzip -k test_input.txt
[ -f test_input.txt.lz ] || { echo "FAIL: .lz file not created"; exit 1; }

# Decompress (keep compressed with -k, output to specified file with -o)
lzip -dk -o test_output.txt test_input.txt.lz
[ -f test_output.txt ] || { echo "FAIL: output file not created"; exit 1; }

# Verify roundtrip integrity
if cmp -s test_input.txt test_output.txt; then
  echo "PASS: roundtrip integrity verified"
else
  echo "FAIL: roundtrip integrity check failed"
  exit 1
fi

# Cleanup
rm -f test_input.txt test_input.txt.lz test_output.txt
