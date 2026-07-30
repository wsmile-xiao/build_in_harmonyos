#!/bin/sh
# Smoke test for mecab-ko 0.996-ko-0.9.2
set -euo pipefail

echo "=== mecab-ko test_package smoke test ==="

# Test 1: mecab --version
mecab --version 2>&1 | grep -q "0.996/ko-0.9.2"
echo "PASS: mecab --version shows 0.996/ko-0.9.2"

# Test 2: mecab-config --version
mecab-config --version > /dev/null 2>&1
echo "PASS: mecab-config --version"

# Test 3: mecab-dict-index --help
mecab-dict-index --help > /dev/null 2>&1
echo "PASS: mecab-dict-index --help"

# Test 4: mecab-dict-gen --help
mecab-dict-gen --help > /dev/null 2>&1
echo "PASS: mecab-dict-gen --help"

# Test 5: mecab-cost-train --help
mecab-cost-train --help > /dev/null 2>&1
echo "PASS: mecab-cost-train --help"

echo ""
echo "All 5 smoke tests passed."
