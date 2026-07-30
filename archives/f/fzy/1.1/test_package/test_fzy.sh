#!/bin/bash
# test_fzy.sh — functional test for fzy binary
# Called by test_package/conanfile.py test() method
# Verifies: version output + non-interactive fuzzy matching
set -euo pipefail

FZY="${1:-fzy}"

# Test 1: version check
"$FZY" --version | grep -q "1.1" || { echo "FAIL: version"; exit 1; }

# Test 2: functional fuzzy matching (-e = show-matches, -s = scores)
result=$(printf "apple\nbanana\ncherry\napricot\ngrape\npineapple\n" | "$FZY" -e "ap" -s)
echo "$result" | grep -q "apple" || { echo "FAIL: apple not in results"; exit 1; }
echo "$result" | grep -q "apricot" || { echo "FAIL: apricot not in results"; exit 1; }

echo "All tests passed"
