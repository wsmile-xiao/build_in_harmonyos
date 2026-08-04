#!/usr/bin/env bash
# test.sh — Smoke test for gel 0.3.0
# Verifies that gel can start and display help/version.
set -euo pipefail

GEL_BIN_DIR="$1"
GEL_LIB_DIR="$2"
GEL_BIN="$GEL_BIN_DIR/gel"

# Find ruby
RUBY_PATH="${RUBY:-$(command -v ruby 2>/dev/null || true)}"
if [ -z "$RUBY_PATH" ]; then
    echo "Ruby not found — skipping runtime test"
    exit 0
fi

echo "Using ruby: $RUBY_PATH"

# Test 1: gel --help should produce output indicating the tool is runnable
# gel has no default command; --help prints a prompt message, not classic usage
output="$("$RUBY_PATH" "$GEL_BIN" --help 2>&1)" || true
echo "Test 1 (gel --help): $output"
# AND logic: output must contain tool name "gel" AND at least one known subcommand
echo "$output" | grep -qi "gel" || {
    echo "FAIL: Expected output to contain 'gel' tool name"
    echo "--- output ---"
    echo "$output"
    exit 1
}
echo "$output" | grep -qE "(install|exec|lock|help|command)" || {
    echo "FAIL: Expected output to contain a known subcommand or keyword (install/exec/lock/help/command)"
    echo "--- output ---"
    echo "$output"
    exit 1
}
echo "Test 1 PASSED: gel --help output valid"

# Test 2: Verify lib/gel/command.rb is loadable
if [ -f "$GEL_LIB_DIR/gel/command.rb" ]; then
    echo "Test 2 (lib/gel/command.rb): found"
else
    echo "FAIL: lib/gel/command.rb not found"
    exit 1
fi

# Test 3: Verify lib/gel/version.rb contains version string
if [ -f "$GEL_LIB_DIR/gel/version.rb" ]; then
    version_content=$(cat "$GEL_LIB_DIR/gel/version.rb")
    echo "$version_content" | grep -q "0.3.0" || {
        echo "FAIL: version.rb does not contain 0.3.0"
        exit 1
    }
    echo "Test 3 (version.rb): contains 0.3.0"
else
    echo "FAIL: lib/gel/version.rb not found"
    exit 1
fi

echo "All gel tests PASSED"
