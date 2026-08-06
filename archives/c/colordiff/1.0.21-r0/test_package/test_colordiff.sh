#!/usr/bin/env bash
# R34: real smoke test for colordiff 1.0.21-r0 — exercises the packaged artifact.
# colordiff is a Perl script wrapper around diff; we verify presence, executable
# bit, shebang, perl syntax, and --help output (exits 0).
set -u

BIN_DIR="${1:?usage: test_colordiff.sh <package bin dir>}"

FAIL=0

# Check colordiff and cdiff exist and are executable
for f in colordiff cdiff; do
    if [ ! -x "$BIN_DIR/$f" ]; then
        echo "FAIL: $f missing or not executable in $BIN_DIR"
        FAIL=1
    fi
done

# Verify shebang is env perl
COLORDIFF="$BIN_DIR/colordiff"
if [ -f "$COLORDIFF" ]; then
    SHEBANG=$(head -1 "$COLORDIFF")
    if [[ "$SHEBANG" != *"env perl"* ]]; then
        echo "FAIL: unexpected shebang: $SHEBANG"
        FAIL=1
    fi
    # Perl syntax check
    if ! perl -c "$COLORDIFF" 2>/dev/null; then
        echo "FAIL: colordiff perl syntax check failed"
        FAIL=1
    fi
    # Execute colordiff --help (recognized option, exits 0)
    # Use perl directly to avoid shebang PATH issues in test env
    if ! perl "$COLORDIFF" --help >/dev/null 2>&1; then
        echo "FAIL: colordiff --help execution failed"
        FAIL=1
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "colordiff smoke test: OK"
fi
exit "$FAIL"
