#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/fatsort" >&2
  exit 2
fi

fatsort_bin="$1"

if [ ! -x "$fatsort_bin" ]; then
  echo "fatsort binary is not executable: $fatsort_bin" >&2
  exit 1
fi

"$fatsort_bin" -v
"$fatsort_bin" -h
