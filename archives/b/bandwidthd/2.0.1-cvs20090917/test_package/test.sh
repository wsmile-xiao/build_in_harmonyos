#!/bin/sh
set -eu

bandwidthd_bin="${BANDWIDTHD_TEST_BINARY:-bandwidthd}"
help_output="$("$bandwidthd_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Usage: bandwidthd" >/dev/null
printf '%s\n' "$help_output" | grep -F -- "--help" >/dev/null

# Exercise the libpcap device-enumeration path without starting a capture
# daemon or requiring a privileged interface.
test_config="${TMPDIR:-/tmp}/bandwidthd-test.$$.conf"
mkdir -p "${TMPDIR:-/tmp}"
trap 'rm -f "$test_config"' EXIT
printf '%s\n' 'subnet 127.0.0.0 255.0.0.0' > "$test_config"
"$bandwidthd_bin" -c "$test_config" -l >/dev/null

echo "bandwidthd CLI checks passed"
