#!/usr/bin/env bash
set -euo pipefail

fstcompile="$1"
header="$2"
libfst="$3"

test -x "$fstcompile"
test -f "$header"
test -e "$libfst"
export LD_LIBRARY_PATH="$(dirname "$libfst"):${LD_LIBRARY_PATH:-}"
help_output="$("$fstcompile" --help 2>&1 || true)"
printf '%s\n' "$help_output" | grep -E "fstcompile|Usage"
echo "PASS openfst artifacts"
