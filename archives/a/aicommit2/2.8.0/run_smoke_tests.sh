#!/bin/sh
set -eu

app_dir=$1
cli="$app_dir/dist/cli.mjs"

version=$(node --jitless "$cli" --version)
test "$version" = "2.8.0"

help=$(node --jitless "$cli" --help)
printf '%s\n' "$help" | grep -q "aicommit2 v2.8.0"
printf '%s\n' "$help" | grep -q "config"
printf '%s\n' "$help" | grep -q "doctor"

echo "aicommit2 upstream CLI smoke tests passed"
