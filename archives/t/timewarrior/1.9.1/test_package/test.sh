#!/usr/bin/env bash
set -euo pipefail
output=$("$1" --version 2>&1) || {
    status=$?
    printf '%s\n' "$output" >&2
    exit "$status"
}
printf '%s\n' "$output" | grep -qE "^(timew |Timewarrior )?1\.9\.1$"
