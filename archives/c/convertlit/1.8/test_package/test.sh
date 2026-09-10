#!/usr/bin/env sh
set -eu

clit="$1"

set +e
usage_output="$("$clit" 2>&1)"
usage_status=$?
set -e
test "$usage_status" -ne 0
printf '%s\n' "$usage_output" | grep -F "ConvertLIT (Version 1.8)" >/dev/null

workdir="$PWD/convertlit-test-$$"
mkdir -p "$workdir/exploded"
trap 'rm -rf "$workdir"' EXIT HUP INT TERM
printf '%s' 'fake .lit file content' > "$workdir/test.lit"

set +e
error_output="$("$clit" "$workdir/test.lit" "$workdir/exploded" 2>&1)"
error_status=$?
set -e
test "$error_status" -ne 0
printf '%s\n' "$error_output" | grep -F "LIT FORMAT ERROR: File is too small" >/dev/null

echo "convertlit functional tests passed"
