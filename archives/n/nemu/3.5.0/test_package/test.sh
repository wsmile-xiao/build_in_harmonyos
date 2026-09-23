#!/usr/bin/env bash
set -euo pipefail

nemu="$1"
output="$("$nemu" --version)"
printf '%s\n' "$output"
grep -Eq 'nemu|3\.5\.0|v3\.5\.0' <<< "$output"
