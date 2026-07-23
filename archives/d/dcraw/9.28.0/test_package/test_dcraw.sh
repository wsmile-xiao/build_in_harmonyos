#!/bin/sh
set -eu

binary=${1:?dcraw binary path is required}
output=$(mktemp "${TMPDIR:-.}/dcraw-test.XXXXXX")
trap 'rm -f "$output"' EXIT HUP INT TERM

# dcraw prints its banner and usage text without arguments and intentionally
# returns status 1 for this invocation.
set +e
"$binary" >"$output" 2>&1
status=$?
set -e

if [ "$status" -ne 1 ]; then
    echo "dcraw returned $status, expected 1" >&2
    cat "$output" >&2
    exit 1
fi

if ! grep -F 'Raw photo decoder "dcraw" v9.28' "$output" >/dev/null 2>&1; then
    echo "dcraw version banner not found" >&2
    cat "$output" >&2
    exit 1
fi
