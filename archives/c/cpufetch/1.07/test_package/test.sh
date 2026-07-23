#!/bin/bash
set -euo pipefail

command -v cpufetch >/dev/null

if ! output="$(cpufetch 2>&1)"; then
    printf '%s\n' 'ERROR: cpufetch execution failed' >&2
    exit 1
fi
test -n "$output"
printf '%s\n' "$output" | grep -Eiq 'cpu|name|architecture'

if ! help_output="$(cpufetch --help 2>&1)"; then
    printf '%s\n' 'ERROR: cpufetch --help failed' >&2
    exit 1
fi
printf '%s\n' "$help_output" | grep -Eiq 'usage|options'

printf '%s\n' "$output"
