#!/bin/sh
# Consumer smoke test for leaps 0.9.1 (test_package test source).
#
# Executes the INSTALLED leaps binary the way a real user would:
#   --help prints the "Usage: leaps" banner and exits.
#
# Invoked from test_package/conanfile.py test() with the absolute path
# to the packaged binary as $1 (caddy test.sh precedent; R34 — real
# binary execution, not an empty shell test).
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-leaps>" >&2
    exit 2
fi

leaps_bin="$1"

if [ ! -f "$leaps_bin" ]; then
    echo "leaps binary not found: $leaps_bin" >&2
    exit 1
fi

help_output="$("$leaps_bin" --help 2>&1 || true)"
printf '%s\n' "$help_output" | grep -F "Usage: leaps" >/dev/null

echo "leaps 0.9.1 consumer smoke: --help banner OK"
