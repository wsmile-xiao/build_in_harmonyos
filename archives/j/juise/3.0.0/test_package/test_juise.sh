#!/bin/sh
# test_juise.sh — verify juise command-line tools are installed and run.
# Usage: test_juise.sh <path-to-juise-package-folder>

set -e

PKG_DIR="$1"

if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder not provided"
    exit 1
fi

BIN_DIR="$PKG_DIR/bin"
LIB_DIR="$PKG_DIR/lib"

ASSERTION_COUNT=0
pass() {
    ASSERTION_COUNT=$((ASSERTION_COUNT + 1))
    echo "PASS: $1"
}
fail() {
    echo "FAIL: $1"
    exit 1
}

# Test 1: juise binary exists and is executable
if [ ! -x "$BIN_DIR/juise" ]; then
    fail "$BIN_DIR/juise not found or not executable"
fi
pass "juise binary present and executable"

# Test 2: juise --version runs and reports version 3.0.0
version_output=$("$BIN_DIR/juise" --version 2>&1) || fail "juise --version failed to run"
echo "$version_output" | grep -q "3.0.0" || fail "juise --version should report 3.0.0, got: $version_output"
pass "juise --version reports 3.0.0"

# Test 3: juise --help shows usage
help_output=$("$BIN_DIR/juise" --help 2>&1) || true
echo "$help_output" | grep -qi "usage" || fail "juise --help should show usage"
pass "juise --help shows usage"

# Test 4: libjuise shared library present
lib_juise=$(ls "$LIB_DIR"/libjuise.so* 2>/dev/null | head -1) || true
if [ -z "$lib_juise" ]; then
    fail "libjuise shared library not found in $LIB_DIR"
fi
pass "libjuise shared library present"

echo ""
echo "All $ASSERTION_COUNT assertions passed."
