#!/usr/bin/env bash
set -euo pipefail

xinit_bin="$1"
startx_bin="$2"

test -x "$xinit_bin"
test -x "$startx_bin"
"$BASH" -n "$startx_bin"

log="$PWD/xinit-smoke.log"
set +e
"$xinit_bin" "$PWD/missing-xinit-client" -- "$PWD/missing-xinit-server" :99 >"$log" 2>&1
status=$?
set -e

test "$status" -ne 0
grep -Eq "unable to run server|No such file|not found" "$log"
echo "PASS xinit tools"
