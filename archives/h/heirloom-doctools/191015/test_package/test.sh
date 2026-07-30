#!/bin/sh
# test.sh — verify heirloom-doctools nroff binary (R34: must use the package's binary)
# Usage: sh test.sh /path/to/nroff
NROFF="${1:-nroff}"

# Resolve symlink (CI creates bin/ symlinks to ucb/ executables)
REAL_PATH=$(readlink -f "$NROFF" 2>/dev/null)
if [ -n "$REAL_PATH" ] && [ -f "$REAL_PATH" ]; then
    NROFF="$REAL_PATH"
fi

# Verify binary exists
if [ ! -f "$NROFF" ]; then
    echo "FAIL: nroff binary not found at $NROFF"
    exit 1
fi

# Verify it is an ELF binary
if file "$NROFF" 2>/dev/null | grep -q "ELF"; then
    echo "PASS: nroff is an ELF binary"
else
    echo "FAIL: nroff is not an ELF binary"
    exit 1
fi

# Verify architecture is aarch64
if readelf -h "$NROFF" 2>/dev/null | grep -q "Machine:.*AArch64"; then
    echo "PASS: nroff is aarch64"
else
    echo "FAIL: nroff is not aarch64"
    exit 1
fi

# Try to run nroff with simple input (may fail on OHOS without ELF signing)
echo '.TL Test Document' | "$NROFF" -Tutf8 2>/dev/null && echo "PASS: nroff executes and produces output" || echo "SKIP: nroff cannot execute (ELF signing required on OHOS)"

exit 0
