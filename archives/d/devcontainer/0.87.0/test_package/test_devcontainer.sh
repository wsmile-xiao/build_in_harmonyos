#!/bin/bash
# Verify the packaged devcontainer CLI wrapper.
# Tests: wrapper exists, version output, help output.

set -euo pipefail

DEVCONTAINER_BIN="${1:-}"

if [ -z "$DEVCONTAINER_BIN" ]; then
    echo "ERROR: devcontainer binary path is required"
    exit 1
fi

if [ ! -x "$DEVCONTAINER_BIN" ]; then
    echo "ERROR: $DEVCONTAINER_BIN not found or not executable"
    exit 1
fi

# Test 1: Version output
output="$("$DEVCONTAINER_BIN" --version 2>&1)"
echo "Version: $output"
echo "$output" | grep -F "0.87.0"

# Test 2: Help output (yargs shows "Options:" not "Usage:")
help_output="$("$DEVCONTAINER_BIN" --help 2>&1)"
echo "$help_output" | grep -F "Options:"

echo "PASS: devcontainer wrapper, version output, and help output are valid"
