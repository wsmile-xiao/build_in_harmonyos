#!/bin/bash
# test.sh — lynis test_package test script
# Verifies that the installed lynis script is syntactically valid and runs correctly

set -euo pipefail

# Find lynis binary - it should be in PATH via VirtualRunEnv
LYNIS_BIN=$(which lynis 2>/dev/null || true)

if [ -z "$LYNIS_BIN" ]; then
    echo "ERROR: lynis not found in PATH"
    exit 1
fi

echo "Found lynis at: $LYNIS_BIN"

# Syntax check
sh -n "$LYNIS_BIN" && echo "Syntax check: PASS" || {
    echo "ERROR: Syntax check failed"
    exit 1
}

# Actually run lynis --version (R34: not just syntax check)
"$LYNIS_BIN" --version || {
    echo "ERROR: lynis --version failed"
    exit 1
}

echo "All tests passed."
