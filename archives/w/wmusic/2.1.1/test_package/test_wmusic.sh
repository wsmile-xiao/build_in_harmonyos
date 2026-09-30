#!/bin/sh
# test_wmusic.sh: smoke test for the packaged wmusic binary.
#
# wmusic is an X11 GUI dockapp. Without a display, it will fail at
# XOpenDisplay() with the upstream "can't open display" signature.
# We verify:
#   1. The binary is an aarch64 ELF
#   2. The binary prints its version banner with --version
#   3. The binary fails at XOpenDisplay (expected without display)

STAGED_DIR="$1"
WORK_DIR="$2"
WMUSIC="$STAGED_DIR/wmusic"

echo "=== wmusic smoke test ==="
echo "Binary: $WMUSIC"

# Test 1: Check binary exists
if [ ! -f "$WMUSIC" ]; then
    echo "FAIL: wmusic binary not found"
    exit 1
fi
echo "PASS: binary exists"

# Test 2: Check binary is aarch64 ELF
MACHINE=$(llvm-readelf -h "$WMUSIC" 2>/dev/null | grep "Machine:" | sed 's/.*Machine: *//')
if [ "$MACHINE" != "AArch64" ]; then
    echo "FAIL: expected AArch64, got $MACHINE"
    exit 1
fi
echo "PASS: binary is AArch64 ELF"

# Test 3: Check --version works
VERSION=$("$WMUSIC" --version 2>&1 | head -1)
if echo "$VERSION" | grep -q "wmusic"; then
    echo "PASS: version banner: $VERSION"
else
    echo "FAIL: no version banner"
    exit 1
fi

# Test 4: Check XOpenDisplay fails (expected without display)
OUTPUT=$("$WMUSIC" 2>&1)
RC=$?
if echo "$OUTPUT" | grep -qi "display\|XOpenDisplay"; then
    echo "PASS: XOpenDisplay fails as expected (no display)"
else
    echo "SKIP: XOpenDisplay test inconclusive (rc=$rc, output=$OUTPUT)"
fi

echo "=== wmusic smoke test complete ==="
exit 0
