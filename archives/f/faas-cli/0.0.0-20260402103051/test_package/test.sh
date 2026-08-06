#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-faas-cli>" >&2
    exit 2
fi

faas_cli_bin="$1"

if [ ! -f "$faas_cli_bin" ]; then
    echo "faas-cli binary not found: $faas_cli_bin" >&2
    exit 1
fi

# Verify --help works
"$faas_cli_bin" --help >/dev/null

# Verify version output contains expected version string
version_output="$("$faas_cli_bin" version)"

printf '%s\n' "$version_output" | grep -F "0.0.0-20260402103051" >/dev/null
printf '%s\n' "$version_output" | grep -F "bf309592" >/dev/null
printf '%s\n' "$version_output" | grep -F "CLI:" >/dev/null
