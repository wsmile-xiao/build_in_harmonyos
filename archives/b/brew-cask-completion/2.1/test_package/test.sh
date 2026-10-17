#!/usr/bin/env bash
# Smoke test for brew-cask-completion 2.1
# Verifies installed completion scripts exist and are non-empty
set -e

PKG_DIR="$1"
if [ -z "$PKG_DIR" ]; then
    echo "Usage: test.sh <package_dir>"
    exit 1
fi

BASH_COMP="$PKG_DIR/share/bash-completion/completions/brew-cask"
FISH_COMP="$PKG_DIR/share/fish/vendor_completions.d/brew-cask.fish"

# Check bash completion script
if [ ! -f "$BASH_COMP" ]; then
    echo "FAIL: bash completion not found at $BASH_COMP"
    exit 1
fi
BASH_SIZE=$(wc -c < "$BASH_COMP")
if [ "$BASH_SIZE" -lt 1000 ]; then
    echo "FAIL: bash completion too small ($BASH_SIZE bytes)"
    exit 1
fi
echo "OK: bash completion script ($BASH_SIZE bytes)"

# Check fish completion script
if [ ! -f "$FISH_COMP" ]; then
    echo "FAIL: fish completion not found at $FISH_COMP"
    exit 1
fi
FISH_SIZE=$(wc -c < "$FISH_COMP")
if [ "$FISH_SIZE" -lt 1000 ]; then
    echo "FAIL: fish completion too small ($FISH_SIZE bytes)"
    exit 1
fi
echo "OK: fish completion script ($FISH_SIZE bytes)"

# Verify bash syntax
bash -n "$BASH_COMP" 2>&1 || {
    echo "FAIL: bash syntax check failed"
    exit 1
}
echo "OK: bash syntax check passed"

echo "All smoke tests passed."
