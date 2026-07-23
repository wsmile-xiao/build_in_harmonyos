#!/usr/bin/env bash
set -euo pipefail
output=$("$1" --version 2>&1) || {
    status=$?
    printf '%s\n' "$output" >&2
    exit "$status"
}
printf '%s\n' "$output" | grep -i "glslang"

"$1" -V "$2" -o "$3"
test -s "$3"
magic=$(od -An -N4 -tx1 "$3" | tr -d ' \n')
if [[ "$magic" != "03022307" ]]; then
    printf 'unexpected SPIR-V magic: %s\n' "$magic" >&2
    exit 1
fi
