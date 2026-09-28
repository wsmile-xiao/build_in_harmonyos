#!/bin/sh
# Real consumer test for the installed jdupes executable.
set -eu

command -v jdupes >/dev/null 2>&1
got_version="$(jdupes --version 2>&1)"
printf '%s\n' "$got_version" | grep -F "jdupes 1.31.1" >/dev/null

test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT HUP INT TERM
mkdir -p "$test_dir/a" "$test_dir/b"
printf 'same-content\n' > "$test_dir/a/duplicate_a.txt"
cp "$test_dir/a/duplicate_a.txt" "$test_dir/b/duplicate_b.txt"
printf 'unique-content\n' > "$test_dir/a/unique.txt"

output="$(jdupes -r "$test_dir" 2>&1)"
printf '%s\n' "$output"
printf '%s\n' "$output" | grep -F "duplicate_a.txt" >/dev/null
printf '%s\n' "$output" | grep -F "duplicate_b.txt" >/dev/null
if printf '%s\n' "$output" | grep -F "unique.txt" >/dev/null; then
    echo "FAIL: unique file was reported as a duplicate" >&2
    exit 1
fi

echo "jdupes 1.31.1 consumer duplicate-file test: OK"
