#!/usr/bin/env bash
set -euo pipefail

fstcompile="$1"
header="$2"
libfst="$3"

test -x "$fstcompile"
test -f "$header"
test -e "$libfst"
"$fstcompile" --help >/dev/null
echo "PASS openfst artifacts"
