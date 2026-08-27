#!/bin/sh
set -euo pipefail

# test_macros.sh — Verify autoconf-archive M4 macros are installed
# Usage: test_macros.sh <aclocal_dir>

ACLOCAL_DIR="${1:-}"

if [ -z "$ACLOCAL_DIR" ]; then
    echo "[fail] aclocal dir argument missing"
    exit 1
fi

if [ ! -d "$ACLOCAL_DIR" ]; then
    echo "[fail] aclocal directory not found: $ACLOCAL_DIR"
    exit 1
fi

MACRO_COUNT=$(ls "$ACLOCAL_DIR"/ax_*.m4 2>/dev/null | wc -l)
if [ "$MACRO_COUNT" -lt 500 ]; then
    echo "[fail] Expected >=500 ax_*.m4 macros, got $MACRO_COUNT"
    exit 1
fi

for macro in ax_absolute_header.m4 ax_pthread.m4 ax_check_compile_flag.m4 ax_cxx_compile_stdcxx.m4; do
    if [ ! -f "$ACLOCAL_DIR/$macro" ]; then
        echo "[fail] Missing macro: $macro"
        exit 1
    fi
done

echo "[ok] autoconf-archive test passed: $MACRO_COUNT ax macros verified"
exit 0
