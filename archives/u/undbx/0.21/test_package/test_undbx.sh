#!/bin/sh
set -eu

version_output=$(undbx --version)
printf '%s\n' "$version_output" | grep -F "UnDBX v0.21 (" >/dev/null

help_output=$(undbx --help)
printf '%s\n' "$help_output" | grep -F "Usage:" >/dev/null
printf '%s\n' "$help_output" | grep -F -- "--recover" >/dev/null

if undbx --not-an-option >/dev/null 2>&1; then
    echo "FAIL: invalid option unexpectedly succeeded" >&2
    exit 1
fi

echo "PASS: version, help, recovery option, and invalid-option behavior verified"
