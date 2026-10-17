#!/bin/sh
# test_bibtex.sh — Functional test for bibtex 0.99e on HarmonyOS
# Runs bibtex --version and processes a .aux file, verifying .bbl output.
# This script is called by test_package/conanfile.py test() method.
set -euo pipefail

BIBTEX_BIN="${1:-bibtex}"
TEST_DIR="${2:-$(dirname "$0")}"

# Test 1: version output
echo "=== Test 1: bibtex --version ==="
"$BIBTEX_BIN" --version

# Test 2: process .aux file with bibtex
echo "=== Test 2: Process .aux file ==="
WORK_DIR=$(mktemp -d 2>/dev/null) || { WORK_DIR="$TEST_DIR/work"; mkdir -p "$WORK_DIR" || exit 1; }
cp "$TEST_DIR/exampl.aux" "$WORK_DIR/xexampl.aux"
cp "$TEST_DIR/xampl.bib" "$WORK_DIR/"
cp "$TEST_DIR/apalike.bst" "$WORK_DIR/"

BIBINPUTS="$WORK_DIR" BSTINPUTS="$WORK_DIR" \
  "$BIBTEX_BIN" "$WORK_DIR/xexampl"

# Verify .bbl output was produced
if [ -f "$WORK_DIR/xexampl.bbl" ]; then
    echo "PASS: bibtex produced .bbl output ($(wc -c < "$WORK_DIR/xexampl.bbl") bytes)"
else
    echo "FAIL: bibtex did not produce .bbl output"
    exit 1
fi

# Cleanup
rm -rf "$WORK_DIR" 2>/dev/null || true
echo "=== All tests passed ==="
