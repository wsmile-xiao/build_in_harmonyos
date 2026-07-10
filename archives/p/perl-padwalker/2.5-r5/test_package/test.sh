#!/bin/sh
# test.sh — perl-padwalker 2.5-r5 consumer test (R34 compliant)
#
# Verifies PadWalker.so is a valid ELF shared library with the expected
# boot_PadWalker XS entry point symbol.
#
# Uses readelf instead of dlopen because PadWalker.so is a Perl XS module
# with unresolved Perl interpreter symbols (Perl_safesysmalloc etc.)
# that require the Perl runtime to resolve at load time.
SO_PATH="$1"

if [ -z "$SO_PATH" ]; then
    echo "FAIL: no .so path provided"
    exit 1
fi

if [ ! -f "$SO_PATH" ]; then
    echo "FAIL: $SO_PATH does not exist"
    exit 1
fi

# 1. Verify ELF format
if ! readelf -h "$SO_PATH" 2>/dev/null | grep -q "ELF"; then
    echo "FAIL: not a valid ELF"
    exit 1
fi

# 2. Verify boot_PadWalker XS entry point symbol exists
if ! readelf -s "$SO_PATH" 2>/dev/null | grep -q "boot_PadWalker"; then
    echo "FAIL: boot_PadWalker symbol not found"
    exit 1
fi

# 3. Verify NEEDED libc.so (only runtime dependency)
if ! readelf -d "$SO_PATH" 2>/dev/null | grep -q "libc.so"; then
    echo "FAIL: libc.so not in NEEDED"
    exit 1
fi

echo "OK: PadWalker.so verified (ELF + boot_PadWalker + libc.so)"
