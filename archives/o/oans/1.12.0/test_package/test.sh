#!/usr/bin/env bash
set -euo pipefail
: "${OANS_BIN:?OANS_BIN must point to the packaged oans executable}"
version="$(${OANS_BIN} --version)"
test "$version" = "oans 1.12.0"
help="$(${OANS_BIN} --help 2>&1)"
printf '%s\n' "$help" | grep -q -- '--version'
version_duperemove="$(duperemove --version)"
test "$version_duperemove" = "oans 1.12.0"
help_duperemove="$(duperemove --help 2>&1)"
test "$(printf '%s\n' "$help_duperemove" | grep -c -- '--version')" -ge 1

workdir="$(mktemp -d "${TMPDIR:-/tmp}/oans-consumer.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
mkdir "$workdir/data"
printf 'consumer duplicate payload\n' > "$workdir/data/first"
cp "$workdir/data/first" "$workdir/data/second"
scan_output="$({ "$OANS_BIN" --hashfile "$workdir/hash.db" -r "$workdir/data"; } 2>&1)"
printf '%s\n' "$scan_output" | grep -q 'Showing 2 identical files'
test -s "$workdir/hash.db"
