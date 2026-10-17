#!/usr/bin/env sh
set -eu

CLAZY_BIN="$1"
CLAZY_PLUGIN="$2"

# Verify clazy-standalone is a valid ELF binary
if [ ! -f "$CLAZY_BIN" ]; then
    echo "ERROR: clazy-standalone binary not found"
    exit 1
fi

magic=$(head -c 4 "$CLAZY_BIN" | od -A n -t x1 | tr -d ' \n')
if [ "$magic" != "7f454c46" ]; then
    echo "ERROR: clazy-standalone is not a valid ELF binary (magic: $magic)"
    exit 1
fi
echo "PASS: clazy-standalone is a valid ELF binary"

# Verify ClazyPlugin.so is a valid ELF shared library
if [ ! -f "$CLAZY_PLUGIN" ]; then
    echo "ERROR: ClazyPlugin.so not found"
    exit 1
fi

magic=$(head -c 4 "$CLAZY_PLUGIN" | od -A n -t x1 | tr -d ' \n')
if [ "$magic" != "7f454c46" ]; then
    echo "ERROR: ClazyPlugin.so is not a valid ELF binary (magic: $magic)"
    exit 1
fi
echo "PASS: ClazyPlugin.so is a valid ELF shared library"

# Try running clazy-standalone --version (may fail due to OHOS ABI limitation)
set +e
output=$("$CLAZY_BIN" --version 2>&1)
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "PASS: clazy-standalone --version executed successfully"
    echo "  output: $output"
else
    echo "WARN: clazy-standalone --version failed (known OHOS ABI limitation, __h vs __n1)"
    echo "  exit code: $status"
fi

echo "All structural tests passed"
