#!/bin/bash
# test_rcm.sh — verify rcm commands (lsrc, mkrc, rcup, rcdn) work correctly.
# Usage: test_rcm.sh <path-to-rcm-package-folder>

set -euo pipefail

PKG_DIR="$1"

if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder not provided"
    exit 1
fi

BIN_DIR="$PKG_DIR/bin"
SHARE_DIR="$PKG_DIR/share/rcm"

# Verify all 4 commands exist and are executable
for cmd in lsrc mkrc rcup rcdn; do
    if [ ! -x "$BIN_DIR/$cmd" ]; then
        echo "ERROR: $BIN_DIR/$cmd not found or not executable"
        exit 1
    fi
done

# Verify share/rcm.sh exists (sourced by all rcm commands)
if [ ! -f "$SHARE_DIR/rcm.sh" ]; then
    echo "ERROR: $SHARE_DIR/rcm.sh not found"
    exit 1
fi

# Create a temporary HOME for dotfile operations
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

export HOME="$WORKDIR"
export RCM_LIB="$SHARE_DIR"
export PATH="$BIN_DIR:$PATH"

ASSERTION_COUNT=0
pass() {
    ASSERTION_COUNT=$((ASSERTION_COUNT + 1))
    echo "PASS: $1"
}
fail() {
    echo "FAIL: $1"
    exit 1
}

# Test 1: lsrc lists dotfiles from ~/.dotfiles
mkdir "$WORKDIR/.dotfiles"
echo "alias ll='ls -l'" > "$WORKDIR/.dotfiles/bashrc"
output=$(lsrc 2>&1) || fail "lsrc failed to run"
echo "$output" | grep -q "bashrc" || fail "lsrc should list bashrc, got: $output"
pass "lsrc correctly lists dotfiles"

# Test 2: rcup creates symlinks from .dotfiles to HOME
rcup 2>&1 || fail "rcup failed to run"
[ -L "$WORKDIR/.bashrc" ] || fail "rcup should create .bashrc symlink"
[ -f "$WORKDIR/.bashrc" ] || fail ".bashrc symlink should resolve to a file"
pass "rcup correctly creates symlinks"

# Test 3: rcdn removes symlinks
rcdn 2>&1 || fail "rcdn failed to run"
[ ! -e "$WORKDIR/.bashrc" ] || fail "rcdn should remove .bashrc symlink"
pass "rcdn correctly removes symlinks"

# Test 4: mkrc moves an existing dotfile into .dotfiles and creates symlink
echo "set number" > "$WORKDIR/.vimrc"
mkrc "$WORKDIR/.vimrc" 2>&1 || fail "mkrc failed to run"
[ -L "$WORKDIR/.vimrc" ] || fail "mkrc should create symlink for .vimrc"
[ -f "$WORKDIR/.dotfiles/vimrc" ] || fail "mkrc should move .vimrc to .dotfiles/vimrc"
pass "mkrc correctly moves dotfile into .dotfiles"

echo ""
echo "All $ASSERTION_COUNT assertions passed."
