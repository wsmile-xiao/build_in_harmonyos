#!/usr/bin/env bash
# Consumer smoke test for wego 2.4.
# Asserts: (1) `wego -h` exits 0; (2-6) stable backend/frontend keywords present.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-wego>" >&2
    exit 2
fi

wego_bin="$1"

if [ ! -f "$wego_bin" ]; then
    echo "wego binary not found: $wego_bin" >&2
    exit 1
fi

# Capture `wego -h` output. wego prints help to stdout on -h and exits 0.
help_output="$("$wego_bin" -h 2>&1)" || {
    echo "wego -h exited non-zero" >&2
    exit 1
}

# Assertion 2: openweathermap backend present
printf '%s\n' "$help_output" | grep -F "openweathermap" >/dev/null
# Assertion 3: weatherapi backend present
printf '%s\n' "$help_output" | grep -F "weatherapi" >/dev/null
# Assertion 4: ascii-art-table frontend present
printf '%s\n' "$help_output" | grep -F "ascii-art-table" >/dev/null
# Assertion 5: markdown frontend present
printf '%s\n' "$help_output" | grep -F "markdown" >/dev/null
# Assertion 6: "Available backends:" header present
printf '%s\n' "$help_output" | grep -F "Available backends:" >/dev/null

echo "wego consumer smoke test: PASS"
