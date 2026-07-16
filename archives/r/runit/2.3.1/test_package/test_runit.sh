#!/usr/bin/env bash
set -euo pipefail
sv_bin="$1"
output="$($sv_bin 2>&1 || true)"
printf '%s\n' "$output" | grep -q usage
