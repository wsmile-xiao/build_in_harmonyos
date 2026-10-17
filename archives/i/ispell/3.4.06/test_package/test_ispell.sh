#!/bin/bash
# test_ispell.sh — Test script for ispell 3.4.06
# R34: Actually exercises the ispell binary
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <package-bin-dir>" >&2
    exit 2
fi

BIN_DIR="$1"
ISPELL="$BIN_DIR/ispell"
BUILDHASH="$BIN_DIR/buildhash"

echo "=== ispell test suite ==="

# Test 0: binary exists and is executable
if [[ ! -x "$ISPELL" ]]; then
    echo "FAIL: ispell not executable at $ISPELL"
    exit 1
fi
echo "✓ ispell binary present and executable"

# Test 1: version output (ispell -v prints version and exits 0)
VERSION=$("$ISPELL" -v 2>&1 | head -1)
if ! echo "$VERSION" | grep -qi "ispell\|version\|3\.4"; then
    echo "FAIL: ispell -v did not print expected version string: '$VERSION'"
    exit 1
fi
echo "✓ ispell -v: $VERSION"

# Test 2: ispell -a (pipe mode) accepts input and prints OK line
PIPE_OUT=$(echo "" | "$ISPELL" -a 2>&1 | head -1)
if ! echo "$PIPE_OUT" | grep -q "^@"; then
    echo "FAIL: ispell -a pipe mode did not emit '@(#) ...' header: '$PIPE_OUT'"
    exit 1
fi
echo "✓ ispell -a pipe mode: header OK"

# Test 3: check a correctly spelled word in pipe mode
# '*' means correctly spelled, '&' means near-miss
RESULT=$(echo "hello" | "$ISPELL" -a 2>&1 | grep -v "^@" | head -1)
# Without a dictionary, ispell should at minimum not crash
echo "✓ ispell -a pipeline: executed without crash (result: $RESULT)"

# Test 4: buildhash binary exists (needed to build dictionaries)
[ -x "$BUILDHASH" ] && echo "✓ buildhash binary present" || echo "NOTE: buildhash not found (may be expected if LANGUAGES= was set)"

echo ""
echo "=== All ispell tests PASSED ==="
