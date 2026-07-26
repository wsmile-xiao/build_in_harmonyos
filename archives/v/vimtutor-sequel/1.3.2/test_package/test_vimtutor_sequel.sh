#!/bin/sh
set -eu

PKG_DIR="$1"
BIN_PATH="$PKG_DIR/bin/vimtutor-sequel"
TUTORIAL_FILE="$PKG_DIR/share/vimtutor-sequel/vimtutor-sequel.txt"
VIMRC_FILE="$PKG_DIR/share/vimtutor-sequel/vimtutor-sequel.vimrc"

if [ ! -f "$BIN_PATH" ]; then
    echo "ERROR: vimtutor-sequel binary not found at $BIN_PATH"
    exit 1
fi

if [ ! -f "$TUTORIAL_FILE" ]; then
    echo "ERROR: tutorial file not found at $TUTORIAL_FILE"
    exit 1
fi

if [ ! -f "$VIMRC_FILE" ]; then
    echo "ERROR: vimrc file not found at $VIMRC_FILE"
    exit 1
fi

if grep -F "brew --prefix" "$BIN_PATH" >/dev/null 2>&1; then
    echo "ERROR: Homebrew-specific path logic still exists in installed script"
    exit 1
fi

if grep -F "/tmp/vimtutor-sequel.txt" "$BIN_PATH" >/dev/null 2>&1; then
    echo "ERROR: fixed /tmp path still exists in installed script"
    exit 1
fi

BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
    if command -v bash >/dev/null 2>&1; then
        BASH_BIN="$(command -v bash)"
    elif [ -x /data/service/hnp/bin/bash ]; then
        BASH_BIN="/data/service/hnp/bin/bash"
    else
        echo "ERROR: bash not found for running vimtutor-sequel"
        exit 1
    fi
fi

VERSION_OUTPUT="$("$BASH_BIN" "$BIN_PATH" --version)"
printf '%s\n' "$VERSION_OUTPUT"
printf '%s\n' "$VERSION_OUTPUT" | grep -F "Vimtutor Sequel version 1.3.2" >/dev/null
