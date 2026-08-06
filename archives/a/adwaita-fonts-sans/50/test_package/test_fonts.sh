#!/usr/bin/env bash
# test_fonts.sh — Verify Adwaita Sans font files are installed correctly
# This is a data-only package test for adwaita-fonts-sans.

set -euo pipefail

FONTS_DIR="$1"
if [ -z "$FONTS_DIR" ]; then
    echo "Usage: $0 <fonts_dir>"
    exit 1
fi

echo "Checking fonts in: $FONTS_DIR"

# Check directory exists
if [ ! -d "$FONTS_DIR" ]; then
    echo "FAIL: Fonts directory not found: $FONTS_DIR"
    exit 1
fi

# Check expected font files exist and have reasonable size
EXPECTED_FONTS=("AdwaitaSans-Regular.ttf" "AdwaitaSans-Italic.ttf")
MIN_SIZE=100000

for font_name in "${EXPECTED_FONTS[@]}"; do
    font_path="$FONTS_DIR/$font_name"
    if [ ! -f "$font_path" ]; then
        echo "FAIL: Font file not found: $font_path"
        exit 1
    fi
    size=$(wc -c < "$font_path")
    if [ "$size" -lt "$MIN_SIZE" ]; then
        echo "FAIL: Font file $font_name too small: $size bytes (min: $MIN_SIZE)"
        exit 1
    fi
    echo "  OK: $font_name ($size bytes)"
done

echo "PASS: All ${#EXPECTED_FONTS[@]} Adwaita Sans font files verified"
exit 0