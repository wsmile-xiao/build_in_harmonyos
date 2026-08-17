#!/bin/sh
set -eu

BIN="$1"

TEST_HOME="$PWD/abbtr-test-home"
rm -rf "$TEST_HOME"
mkdir -p "$TEST_HOME/.local/bin"
mkdir -p "$TEST_HOME/.config/abbtr"

export HOME="$TEST_HOME"
export PATH="$HOME/.local/bin:$PATH"

VERSION_OUTPUT="$("$BIN" -v)"
echo "$VERSION_OUTPUT"
echo "$VERSION_OUTPUT" | grep -F "abbtr version 1.0.4"

HELP_OUTPUT="$("$BIN" -h)"
echo "$HELP_OUTPUT"
echo "$HELP_OUTPUT" | grep -F "Usage: abbtr <option>"
echo "$HELP_OUTPUT" | grep -F "Available options:"
