#!/usr/bin/env bash
set -euo pipefail

for tool in po4a po4a-gettextize po4a-translate po4a-updatepo msguntypot; do
  path="$(command -v "$tool")"
  test -n "$path"
  test -x "$path"
done

perl -MLocale::Po4a::Po -e 'print "Locale::Po4a::Po loaded\n"'

version_output="$(po4a --version 2>&1)"
printf '%s\n' "$version_output"
printf '%s\n' "$version_output" | grep -F "po4a version 0.74"

echo "po4a smoke test: PASS"
