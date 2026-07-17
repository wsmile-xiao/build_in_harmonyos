#!/usr/bin/env bash
set -euo pipefail

xinit_bin="$1"
startx_bin="$2"

test -x "$xinit_bin"
test -x "$startx_bin"
"$xinit_bin" -version >/dev/null 2>&1 || "$xinit_bin" --version >/dev/null 2>&1 || test -x "$xinit_bin"
echo "PASS xinit tools"
