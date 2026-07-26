#!/usr/bin/env bash
set -euo pipefail

ANYENV_BIN="$1"
EXPECTED_ROOT="$2"

version_output="$("$ANYENV_BIN" --version)"
case "$version_output" in
  "anyenv 1.1.5"*) ;;
  *) echo "unexpected version output: $version_output" >&2; exit 1 ;;
esac

root_output="$("$ANYENV_BIN" root)"
test "$root_output" = "$EXPECTED_ROOT"

commands_output="$("$ANYENV_BIN" commands)"
echo "$commands_output" | grep -E '(^|[[:space:]])root($|[[:space:]])' >/dev/null
echo "$commands_output" | grep -E '(^|[[:space:]])commands($|[[:space:]])' >/dev/null
