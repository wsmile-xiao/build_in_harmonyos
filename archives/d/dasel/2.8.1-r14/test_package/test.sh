#!/usr/bin/env bash
# test_package/test.sh — Run dasel --version, JSON select, YAML convert, and put command tests
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-dasel>" >&2
    exit 2
fi

dasel_bin="$1"

if [ ! -f "$dasel_bin" ]; then
    echo "dasel binary not found: $dasel_bin" >&2
    exit 1
fi

# Test --version
version_output="$("$dasel_bin" --version)"
printf '%s\n' "$version_output" | grep -F "v2.8.1" >/dev/null

# Test JSON select
echo '{"name":"test","value":42}' | "$dasel_bin" -r json '.name' | grep -F "test" >/dev/null

# Test JSON to YAML conversion
echo '{"name":"test"}' | "$dasel_bin" -r json -w yaml '.' | grep -F "name" >/dev/null

# Test put command
echo '{"name":"old"}' | "$dasel_bin" put -r json -v 'new' '.name' | grep -F "new" >/dev/null
