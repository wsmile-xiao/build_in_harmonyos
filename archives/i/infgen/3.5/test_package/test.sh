#!/bin/bash
set -euo pipefail

command -v infgen >/dev/null

# 1. Help/version output is deterministic (IG_VERSION baked into the binary).
help_out="$(infgen -h 2>&1)"
printf '%s\n' "$help_out" | grep -F "infgen 3.5"
printf '%s\n' "$help_out" | grep -F "Usage"

# 2. Disassemble an empty gzip stream. The 20-byte input is a gzip container
#    (mtime=0) wrapping an empty stored deflate block, so the output is fully
#    deterministic and requires no external compressor on the device.
empty_gz='\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\x0a\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
out="$(printf "$empty_gz" | infgen 2>&1)"
printf '%s\n' "$out" | grep -F "! infgen 3.5 output"
