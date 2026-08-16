#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /path/to/pppd" >&2
    exit 2
fi

pppd=$1

version_output=$("$pppd" --version 2>&1)
test "$version_output" = "pppd version 2.5.2"

help_output=$("$pppd" --help 2>&1)
printf '%s\n' "$help_output" | grep -F "where options are:" >/dev/null

# The early parser must remain an exact informational-option allowlist.
# A normal option that names a missing file must still follow the original
# configuration path and fail closed.
missing_options="${TMPDIR:-.}/pppd-options-must-not-exist-$$"
test ! -e "$missing_options"
if "$pppd" file "$missing_options" >/dev/null 2>&1; then
    echo "pppd unexpectedly bypassed normal option processing" >&2
    exit 1
fi
