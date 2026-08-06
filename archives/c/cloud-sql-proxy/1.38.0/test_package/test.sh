#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-cloud-sql-proxy>" >&2
    exit 2
fi

csp_bin="$1"

if [ ! -f "$csp_bin" ]; then
    echo "cloud-sql-proxy binary not found: $csp_bin" >&2
    exit 1
fi

# Run --version and verify output contains the expected version string
version_output="$("$csp_bin" --version 2>&1)"

printf '%s\n' "$version_output" | grep -F "Cloud SQL Auth proxy" >/dev/null
printf '%s\n' "$version_output" | grep -F "1.38.0" >/dev/null
