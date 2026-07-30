#!/usr/bin/env bash
# test.sh — Smoke test for chruby 0.3.9
# Verifies that chruby-exec is functional after installation.
set -euo pipefail

# Find chruby-exec from the first argument (bin dir)
CHRUBY_BIN_DIR="$1"
CHRUBY_EXEC="$CHRUBY_BIN_DIR/chruby-exec"

# Find bash
BASH_PATH="${CONFIG_SHELL:-${SHELL:-$(command -v bash)}}"
BASH_DIR="$(dirname "$BASH_PATH")"
export PATH="$CHRUBY_BIN_DIR:$BASH_DIR:$PATH"

# Test 1: chruby-exec --version should output version string
output="$("$BASH_PATH" "$CHRUBY_EXEC" --version 2>&1)"
echo "Test 1 (chruby-exec --version): $output"
echo "$output" | grep -q "chruby version 0.3.9" || {
    echo "FAIL: Expected 'chruby version 0.3.9' in output"
    exit 1
}

# Test 2: chruby-exec --help should show usage
output="$("$BASH_PATH" "$CHRUBY_EXEC" --help 2>&1)"
echo "Test 2 (chruby-exec --help): $output"
echo "$output" | grep -q "usage" || {
    echo "FAIL: Expected 'usage' in help output"
    exit 1
}

echo "All chruby tests PASSED"
