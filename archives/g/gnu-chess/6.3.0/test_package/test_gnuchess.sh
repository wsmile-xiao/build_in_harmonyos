#!/bin/sh
set -eu

"$1" --version

status=0
help_output=$("$1" --help 2>&1) || status=$?
[ "$status" -eq 0 ] || [ "$status" -eq 1 ]
printf '%s\n' "$help_output" | grep -q "Usage:"
printf '%s\n' "$help_output" | grep -q -- "--uci"
