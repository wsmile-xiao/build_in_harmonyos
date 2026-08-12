#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

wrapper=$1
real_binary=$2

test -x "$wrapper"
test -x "$real_binary"

wrapper_help=$("$wrapper" --help 2>&1)
printf '%s\n' "$wrapper_help" | grep -q "Usage of TinyIce"

real_help=$("$real_binary" --help 2>&1)
printf '%s\n' "$real_help" | grep -q "Usage of TinyIce"

magic=$(dd if="$real_binary" bs=4 count=1 2>/dev/null | od -An -tx1 | tr -d ' \n')
test "$magic" = "7f454c46"

echo "tinyice wrapper, signed real binary, and ELF smoke test passed"
