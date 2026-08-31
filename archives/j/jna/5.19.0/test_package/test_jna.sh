#!/bin/bash
# test_jna.sh — verify libjnidispatch.so is a valid JNI bridge library
# Usage: test_jna.sh <path-to-libjnidispatch.so>
set -euo pipefail

LIB_PATH="$1"
if [ -z "$LIB_PATH" ]; then
    echo "FAIL: no library path provided"
    exit 1
fi

if [ ! -f "$LIB_PATH" ]; then
    echo "FAIL: libjnidispatch.so not found at $LIB_PATH"
    exit 1
fi

# Find readelf
READELF=$(which readelf 2>/dev/null || which llvm-readelf 2>/dev/null)
if [ -z "$READELF" ]; then
    echo "FAIL: readelf not found"
    exit 1
fi

# Verify ELF shared object
ELF_TYPE=$($READELF -h "$LIB_PATH" 2>/dev/null | grep "Type:" | awk '{print $2}')
if [ "$ELF_TYPE" != "DYN" ]; then
    echo "FAIL: not a shared object (got $ELF_TYPE, expected DYN)"
    exit 1
fi
echo "PASS: libjnidispatch.so is a valid ELF shared object"

# Verify JNI symbols are exported
if $READELF --dyn-syms --wide "$LIB_PATH" 2>/dev/null | grep -q "Java_com_sun_jna"; then
    echo "PASS: JNI symbols (Java_com_sun_jna_*) found"
else
    echo "FAIL: no Java_com_sun_jna_* symbols found"
    exit 1
fi

echo "test jna 5.19.0: ALL CHECKS PASSED"
