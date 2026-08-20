#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cweb executables
# Runs ctangle and cweave on hello.w and verifies output files.
set -euo pipefail

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$TEST_DIR"

echo "[test] ctangle hello.w"
ctangle hello
if [ ! -s hello.c ]; then
    echo "[fail] ctangle failed: hello.c not created or empty"
    exit 1
fi
echo "[ok] ctangle produced hello.c ($(wc -l < hello.c) lines)"

echo "[test] cweave hello.w"
cweave hello
if [ ! -s hello.tex ]; then
    echo "[fail] cweave failed: hello.tex not created or empty"
    exit 1
fi
echo "[ok] cweave produced hello.tex ($(wc -l < hello.tex) lines)"

echo "[test] All tests passed"
