#!/bin/sh
# test_eot_utils.sh — Functional test for eot-utils (mkeot + eotinfo)
# Usage: bash test_eot_utils.sh <bin_dir> [output_dir]
# R34: exercises real binaries, not a stub

set -e

BIN_DIR="$1"
OUTPUT_DIR="${2:-.}"

MKEOT="$BIN_DIR/mkeot"
EOTINFO="$BIN_DIR/eotinfo"

# Verify binaries exist
if [ ! -x "$MKEOT" ]; then
    echo "FAIL: mkeot not found or not executable at $MKEOT"
    exit 1
fi
if [ ! -x "$EOTINFO" ]; then
    echo "FAIL: eotinfo not found or not executable at $EOTINFO"
    exit 1
fi

# Find a system TTF font for testing
TTF_FONT="/system/fonts/FTAeroSans-Regular.ttf"
if [ ! -f "$TTF_FONT" ]; then
    # Fallback: search for any .ttf in /system/fonts
    TTF_FONT=""
    if [ -d /system/fonts ]; then
        for f in /system/fonts/*.ttf; do
            if [ -f "$f" ]; then
                TTF_FONT="$f"
                break
            fi
        done
    fi
fi

if [ -z "$TTF_FONT" ] || [ ! -f "$TTF_FONT" ]; then
    echo "FAIL: No TTF font found in /system/fonts for testing"
    exit 1
fi

# Test 1: mkeot — generate EOT from TTF
EOT_FILE="$OUTPUT_DIR/test_output.eot"
"$MKEOT" "$TTF_FONT" > "$EOT_FILE"

if [ ! -s "$EOT_FILE" ]; then
    echo "FAIL: mkeot did not produce an EOT file (empty or missing)"
    exit 1
fi

echo "PASS: mkeot generated EOT file ($(wc -c < "$EOT_FILE") bytes)"

# Test 2: eotinfo — parse EOT header info
EOT_OUTPUT=$("$EOTINFO" "$EOT_FILE" 2>&1)

if [ -z "$EOT_OUTPUT" ]; then
    echo "FAIL: eotinfo produced no output"
    exit 1
fi

# Verify eotinfo output contains expected fields
if echo "$EOT_OUTPUT" | grep -q "FamilyName"; then
    echo "PASS: eotinfo correctly parsed EOT header"
    echo "$EOT_OUTPUT" | head -5
else
    echo "FAIL: eotinfo output missing FamilyName field"
    echo "$EOT_OUTPUT"
    exit 1
fi

# Cleanup
rm -f "$EOT_FILE"

echo "ALL TESTS PASSED"
