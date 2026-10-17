#!/bin/sh
set -eu

base91="$1"
input="base91-input.txt"
encoded="base91-encoded.txt"
decoded="base91-decoded.txt"

printf 'OpenHarmony base91 round trip\n' > "$input"
"$base91" -o "$encoded" "$input"
"$base91" --decode -o "$decoded" "$encoded"
cmp "$input" "$decoded"
rm -f "$input" "$encoded" "$decoded"
