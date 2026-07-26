#!/usr/bin/env bash
set -euo pipefail

dfu="$1"
test -x "$dfu"
"$dfu" --help >/dev/null
echo "PASS dfu-programmer help"
