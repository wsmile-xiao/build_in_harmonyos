#!/usr/bin/env bash
set -eu

binary="${1:?missing tacd binary path}"
version_output="$("$binary" --version)"
printf '%s\n' "$version_output"
printf '%s\n' "$version_output" | grep -q '0.25.0'

help_output="$("$binary" --help)"
printf '%s\n' "$help_output"
printf '%s\n' "$help_output" | grep -Eiq 'acme|acmeIdentifier|certificate|domain|listen'
