#!/usr/bin/env sh
# test_pstree.sh — test_package for pstree 23.7 (R34)
#
# pstree is a CLI tool that reads /proc to display the process tree.
# This test drives the real binary to verify it can read /proc and
# produce a tree, and checks --version output.
#
# The binary path is passed as $1 by test_package/conanfile.py.
set -u

PSTREE_BIN="$1"
FAILURES=0

check() {
    if eval "$1"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "Testing pstree binary: $PSTREE_BIN"

# Case 1: --version should print version string and exit 0
OUTPUT=$("$PSTREE_BIN" --version 2>&1) && RC=0 || RC=$?
check '[ "$RC" -eq 0 ] && echo "$OUTPUT" | grep -q "pstree.*23.7"' \
    "pstree --version prints version 23.7 and exits 0"

# Case 2: Running pstree with no arguments should produce process tree
# output containing PID numbers in parentheses
OUTPUT=$("$PSTREE_BIN" -p 2>&1) && RC=0 || RC=$?
check '[ "$RC" -eq 0 ] && echo "$OUTPUT" | grep -q "([0-9]"' \
    "pstree -p produces a tree with PIDs"

# Case 3: Running pstree with a specific PID should show that process
# and its children
OUTPUT=$("$PSTREE_BIN" -p 1 2>&1) && RC=0 || RC=$?
check '[ "$RC" -eq 0 ] && [ -n "$OUTPUT" ]' \
    "pstree -p 1 shows process tree for PID 1"

if [ "$FAILURES" -eq 0 ]; then
    echo "All tests passed"
    exit 0
else
    echo "$FAILURES test(s) failed"
    exit 1
fi
