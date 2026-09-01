#!/bin/bash
set -euo pipefail
# test_package test for perl-sereal-decoder 5.004-r3.1
# Verifies Sereal::Decoder XS module package contains expected files.
# Note: .so runtime loading is blocked on OHOS (E046 SELinux), so file-based
# verification is used instead of runtime perl execution.
#
# Usage: bash test.sh <decoder_pkg_folder>

PKG="${1:-}"

# Validate input parameter
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: Package directory not provided or does not exist: '$PKG'"
    echo "Usage: bash test.sh <decoder_pkg_folder>"
    exit 1
fi

PASS=0
TOTAL=0

# 1. Verify Decoder.pm exists in the package
TOTAL=$((TOTAL + 1))
DECODER_PM=$(find "$PKG" -name "Decoder.pm" 2>/dev/null | head -1) || true
if [ -n "$DECODER_PM" ]; then
    PASS=$((PASS + 1))
    echo "OK: Decoder.pm found at $DECODER_PM"
else
    echo "FAIL: Decoder.pm not found in package"
fi

# 2. Verify Constants.pm exists
TOTAL=$((TOTAL + 1))
CONST_PM=$(find "$PKG" -name "Constants.pm" 2>/dev/null | head -1) || true
if [ -n "$CONST_PM" ]; then
    PASS=$((PASS + 1))
    echo "OK: Constants.pm found at $CONST_PM"
else
    echo "FAIL: Constants.pm not found in package"
fi

# 3. Verify Decoder.so exists (XS compilation verification)
TOTAL=$((TOTAL + 1))
DECODER_SO=$(find "$PKG" -name "Decoder.so" 2>/dev/null | head -1) || true
if [ -n "$DECODER_SO" ]; then
    PASS=$((PASS + 1))
    echo "OK: Decoder.so found at $DECODER_SO"
else
    echo "FAIL: Decoder.so not found in package (XS compilation may have failed)"
fi

# 4. Verify Decoder.so is a valid ELF file (binary format check)
TOTAL=$((TOTAL + 1))
if [ -n "$DECODER_SO" ] && [ -f "$DECODER_SO" ]; then
    ELF_MAGIC=$(od -A n -t x1 -N 4 "$DECODER_SO" 2>/dev/null | tr -d ' \n') || true
    if [ "$ELF_MAGIC" = "7f454c46" ]; then
        PASS=$((PASS + 1))
        echo "OK: Decoder.so is valid ELF"
    else
        echo "FAIL: Decoder.so is not a valid ELF file"
    fi
else
    echo "FAIL: Decoder.so not available for ELF check"
fi

# 5. Verify Decoder.pm contains expected module declaration
TOTAL=$((TOTAL + 1))
if [ -n "$DECODER_PM" ] && grep -q "package Sereal::Decoder" "$DECODER_PM" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "OK: Decoder.pm content valid (package Sereal::Decoder)"
else
    echo "FAIL: Decoder.pm content invalid or missing package declaration"
fi

# 6. Verify .so has .codesign section (OHOS ELF signing)
if command -v llvm-readelf >/dev/null 2>&1; then
    TOTAL=$((TOTAL + 1))
    if [ -n "$DECODER_SO" ] && [ -f "$DECODER_SO" ]; then
        if llvm-readelf -S "$DECODER_SO" 2>/dev/null | grep -q ".codesign"; then
            PASS=$((PASS + 1))
            echo "OK: Decoder.so has .codesign section (ELF signed)"
        else
            echo "FAIL: Decoder.so missing .codesign section (not signed for OHOS)"
        fi
    else
        echo "FAIL: Decoder.so not available for codesign check"
    fi
else
    echo "SKIP: llvm-readelf not available, skipping codesign check"
fi

echo "test perl-sereal-decoder 5.004-r3.1: $PASS/$TOTAL OK"
if [ "$PASS" -ne "$TOTAL" ]; then
    echo "FAILED: $PASS/$TOTAL tests passed"
    exit 1
fi
