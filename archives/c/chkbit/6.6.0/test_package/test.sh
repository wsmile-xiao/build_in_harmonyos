#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-chkbit>" >&2
    exit 2
fi

chkbit_bin="$1"

if [ ! -f "$chkbit_bin" ]; then
    echo "chkbit binary not found: $chkbit_bin" >&2
    exit 1
fi

"$chkbit_bin" --help >/dev/null
version_output="$("$chkbit_bin" version)"

printf '%s\n' "$version_output" | grep -F "v6.6.0" >/dev/null
printf '%s\n' "$version_output" | grep -F "github.com/laktak/chkbit" >/dev/null
