#!/bin/bash
set -euo pipefail

# Verify the binary is installed
command -v tcptraceroute >/dev/null

# tcptraceroute requires root for raw sockets, so --help serves as the
# functional smoke check. It exits 1 even when printing usage successfully,
# hence the guarded capture; the grep below is a real assertion.
output="$(tcptraceroute --help 2>&1)" || true
printf '%s\n' "$output" | grep -iF "tcptraceroute"

# Running without args also prints usage — assert it really does
output2="$(tcptraceroute 2>&1)" || true
printf '%s\n' "$output2" | grep -F "Usage"
