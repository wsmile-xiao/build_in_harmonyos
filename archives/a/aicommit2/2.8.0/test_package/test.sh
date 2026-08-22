#!/bin/sh
set -eu

aicommit2=$1

run_launcher() { sh "$aicommit2" "$@"; }

test "$(run_launcher --version)" = "2.8.0"

help=$(run_launcher --help)
printf '%s\n' "$help" | grep -q "aicommit2 v2.8.0"
printf '%s\n' "$help" | grep -q "config"
printf '%s\n' "$help" | grep -q "doctor"

test "$(run_launcher config --help | sed -n '1p')" = "aicommit2 config v2.8.0"

echo "aicommit2 consumer tests passed"
