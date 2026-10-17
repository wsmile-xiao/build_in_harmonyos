#!/usr/bin/env bash
# test_package/test.sh — Run ctop -v and validate version output
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-ctop>" >&2
    exit 2
fi

ctop_bin="$1"

if [ ! -f "$ctop_bin" ]; then
    echo "ctop binary not found: $ctop_bin" >&2
    exit 1
fi

# ctop uses -v flag for version output
version_output="$("$ctop_bin" -v)"

# Verify version string contains expected version
printf '%s\n' "$version_output" | grep -F "0.7.7" >/dev/null

# Verify version string contains "ctop version"
printf '%s\n' "$version_output" | grep -F "ctop version" >/dev/null
