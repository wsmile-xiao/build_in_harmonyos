#!/usr/bin/env bash
# test_package/test.sh — CLI smoke test for mp3check
# Complements conanfile.py test() with a standalone shell-level smoke test.
# Runs in conanrun env (PATH includes installed bin/).
set -euo pipefail

# Test 1: CLI is runnable (--version)
echo "[test] mp3check --version"
output=$(mp3check --version 2>&1) || {
    echo "FAIL: mp3check --version exited non-zero"
    exit 1
}
case "$output" in
    *mp3check*) echo "PASS: --version output contains 'mp3check'" ;;
    *) echo "FAIL: --version output unexpected: $output"; exit 1 ;;
esac

# Test 2: Non-existent path produces diagnostic output
echo "[test] mp3check -e /no/such/file/here.mp3"
output=$(mp3check -e /no/such/file/here.mp3 2>&1 || true)
case "$output" in
    *"stat file"*) echo "PASS: non-existent path diagnosed" ;;
    *) echo "FAIL: non-existent path not diagnosed: $output"; exit 1 ;;
esac

# Test 3: Garbage (non-MPEG) input is rejected
echo "[test] mp3check -e garbage input"
garbage="./smoke_garbage.bin"
printf 'this is not an audio mpeg stream' > "$garbage"
output=$(mp3check -e "$garbage" 2>&1 || true)
rm -f "$garbage"
case "$output" in
    *"not an audio mpeg stream"*) echo "PASS: garbage rejected as non-MPEG" ;;
    *) echo "FAIL: garbage not rejected: $output"; exit 1 ;;
esac

echo "All smoke tests passed."
