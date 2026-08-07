#!/usr/bin/env bash
# test.sh — Smoke test for lice5 5.3.0
# Verifies that script resources are correctly installed.
set -euo pipefail

# Resource directory from the first argument
LICE5_DIR="$1"

# Test 1: Main script lice.epic5 must exist
LICE_EPIC5="$LICE5_DIR/lice/lice.epic5"
if [ ! -f "$LICE_EPIC5" ]; then
    echo "FAIL: Main script not found: $LICE_EPIC5"
    exit 1
fi
echo "OK: lice.epic5 found ($(wc -c < "$LICE_EPIC5") bytes)"

# Test 2: lice/ directory must contain multiple scripts
LICE_COUNT=$(find "$LICE5_DIR/lice" -type f 2>/dev/null | wc -l)
if [ "$LICE_COUNT" -lt 50 ]; then
    echo "FAIL: Expected at least 50 scripts in lice/, got $LICE_COUNT"
    exit 1
fi
echo "OK: lice/ directory contains $LICE_COUNT scripts"

# Test 3: themes/ directory must contain theme files
THEME_COUNT=$(find "$LICE5_DIR/themes" -type f 2>/dev/null | wc -l)
if [ "$THEME_COUNT" -lt 10 ]; then
    echo "FAIL: Expected at least 10 themes, got $THEME_COUNT"
    exit 1
fi
echo "OK: themes/ directory contains $THEME_COUNT theme files"

# Test 4: help/user/ directory must contain help files
HELP_COUNT=$(find "$LICE5_DIR/help/user" -type f 2>/dev/null | wc -l)
if [ "$HELP_COUNT" -lt 10 ]; then
    echo "FAIL: Expected at least 10 help files, got $HELP_COUNT"
    exit 1
fi
echo "OK: help/user/ directory contains $HELP_COUNT help files"

# Test 5: lice.epic5 must contain recognizable LiCe script content
# 精确匹配 "LiCe"（项目特有的混合大小写），不使用 -i，避免误匹配 slice/policy/alice 等
if ! grep -q "LiCe" "$LICE_EPIC5" 2>/dev/null; then
    echo "FAIL: lice.epic5 does not contain expected LiCe script content"
    exit 1
fi
echo "OK: lice.epic5 content verified (LiCe signature found)"

echo "All lice5 tests PASSED"
