#!/bin/bash
set -euo pipefail

command -v ifstat >/dev/null

version_output="$(ifstat -v 2>&1)"
printf '%s\n' "$version_output" | grep -F "ifstat version 1.1"

# Exercise the proc driver and one complete sampling interval.  -a includes
# loopback, so the assertion is deterministic even on an idle CI worker.
sample_output="$(ifstat -a 0.1 1)"
printf '%s\n' "$sample_output" | grep -F "KB/s in"
printf '%s\n' "$sample_output" | grep -F "KB/s out"
printf '%s\n' "$sample_output"
