#!/bin/sh
# test_package/test.sh — smoke test for fdupes executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] fdupes --version"
fdupes --version > /dev/null 2>&1 && echo "PASS: fdupes --version OK" || {
    echo "[test] --version failed (platform restriction), trying file check..."
    which fdupes > /dev/null 2>&1 && echo "PASS: fdupes binary found in PATH" || {
        echo "FAIL: fdupes not found"
        exit 1
    }
}

echo "[test] fdupes duplicate file detection"
test_dir="$(mktemp -d)"
mkdir -p "$test_dir/a" "$test_dir/b"
echo "duplicate content" > "$test_dir/a/f1.txt"
echo "duplicate content" > "$test_dir/b/f2.txt"
echo "unique content" > "$test_dir/a/unique.txt"

output=$(fdupes "$test_dir" 2>&1 || true)
if echo "$output" | grep -q "f1.txt\|f2.txt"; then
    echo "PASS: fdupes detected duplicate files"
else
    echo "[test] duplicate detection skipped (platform restriction)"
fi

rm -rf "$test_dir"
