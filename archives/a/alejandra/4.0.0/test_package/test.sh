#!/usr/bin/env bash
# test_package/test.sh — verify the packaged Alejandra CLI behavior.
set -euo pipefail

version_output="$(alejandra --version 2>/dev/null)"
test "$version_output" = "Alejandra 4.0.0"

formatted_output="$(printf '[ 1 2 ]\n' | alejandra --quiet 2>/dev/null)"
test "$formatted_output" = "[1 2]"

printf '[1 2]\n' | alejandra --check --quiet >/dev/null 2>&1
printf '[ok] Alejandra version, formatting, and check mode passed\n'
