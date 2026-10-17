#!/usr/bin/env bash
# test_package/test.sh — smoke test for clang-complete executable
# Runs in conanrun env (PATH includes installed bin/)
# The binary expects a source file argument; without one it prints:
# "Source file name must be specified as the last commandline argument"
set -eu

echo "[test] clang-complete (no args, expect error message)"
OUTPUT=$(clang-complete 2>&1 || true)

if echo "$OUTPUT" | grep -q "Source file name must be specified"; then
    echo "✅ clang-complete binary runs correctly (links libclang OK)"
    exit 0
else
    echo "❌ unexpected output: $OUTPUT"
    exit 1
fi
