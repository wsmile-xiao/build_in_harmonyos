#!/bin/bash
# test.sh — Verify hypopg PostgreSQL extension shared library
# Checks that hypopg.so exists, is a valid ELF, and has _PG_init symbol
set -euo pipefail

SO_PATH="$1"

if [ ! -f "$SO_PATH" ]; then
    echo "FAIL: hypopg.so not found at $SO_PATH"
    exit 1
fi

# Ensure hnp bin is in PATH for readelf
export PATH="/data/service/hnp/bin:$PATH"

# Check ELF magic number (0x7f 'E' 'L' 'F')
MAGIC=$(od -A n -t x1 -N 4 "$SO_PATH" 2>/dev/null | tr -d ' \n')
if [ "$MAGIC" != "7f454c46" ]; then
    echo "FAIL: $SO_PATH is not a valid ELF file (magic: $MAGIC)"
    exit 1
fi

# Check for _PG_init symbol (PostgreSQL extension entry point)
if ! readelf -s "$SO_PATH" 2>/dev/null | grep "_PG_init" >/dev/null 2>&1; then
    echo "FAIL: _PG_init symbol not found in $SO_PATH"
    exit 1
fi

# Check for hypopg symbols
if ! readelf -s "$SO_PATH" 2>/dev/null | grep "hypopg" >/dev/null 2>&1; then
    echo "FAIL: no hypopg symbols found in $SO_PATH"
    exit 1
fi

echo "PASS: hypopg.so is valid with _PG_init and hypopg symbols"
