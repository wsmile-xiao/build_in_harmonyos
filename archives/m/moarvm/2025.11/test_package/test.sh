#!/usr/bin/zsh
# test_package/test.sh — Execute packaged MoarVM CLI smoke tests.
set -euo pipefail

version_output="$(moar --version)"
printf '%s\n' "$version_output"
printf '%s\n' "$version_output" | grep -F "2025.11"

help_output="$(moar --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "USAGE: moar"
printf '%s\n' "$help_output" | grep -F -- "--full-cleanup"
