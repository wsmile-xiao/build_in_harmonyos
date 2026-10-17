#!/bin/sh

set -eu

PAR_BIN="${1:?path to parchive executable is required}"

printf '%s\n' 'OpenHarmony Parchive functional test' > input.txt
"$PAR_BIN" add -n1 archive.par input.txt
test -f archive.P01
"$PAR_BIN" check archive.par
