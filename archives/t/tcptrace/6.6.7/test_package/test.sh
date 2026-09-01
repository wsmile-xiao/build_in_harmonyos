#!/bin/bash
set -euo pipefail

# Verify the binary is installed and on PATH
command -v tcptrace >/dev/null

# tcptrace with no args prints usage including version info (exits non-zero)
output="$(tcptrace 2>&1)" || true  # tcptrace exits non-zero when no args given
printf '%s\n' "$output" | grep -F "tcptrace"

# -hargs shows detailed version and argument help
args_output="$(tcptrace -hargs 2>&1)" || true  # help output may exit non-zero
printf '%s\n' "$args_output" | grep -iF "version"
