#!/usr/bin/env bash
# newsraft 0.37 consumer smoke tests
set -euo pipefail

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

version_output="$(newsraft -v 2>&1)"
printf '%s\n' "$version_output"
if [[ "$version_output" != *"0.37"* ]]; then
    echo "FAIL: newsraft -v output does not contain 0.37" >&2
    exit 1
fi

newsraft -h >/dev/null 2>&1
printf '%s\n' "PASS: newsraft -v and -h"
