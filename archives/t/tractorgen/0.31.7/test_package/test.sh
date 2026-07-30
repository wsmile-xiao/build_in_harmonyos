#!/data/service/hnp/bin/bash
set -eu

tg_bin="${1:-tractorgen}"

out="$("${tg_bin}" 4)"
printf '%s\n' "$out"

printf '%s\n' "$out" | grep -F "(O)_O_O_(O)" >/dev/null
printf '%s\n' "$out" | grep -F "r-" >/dev/null
