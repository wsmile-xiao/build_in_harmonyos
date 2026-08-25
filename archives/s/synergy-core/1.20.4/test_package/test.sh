#!/bin/sh
set -eu

binary=${1:?synergy-core binary is required}
expected_version=${2:?expected version is required}

version_output=$("$binary" --version)
case "$version_output" in
  *"synergy-core v$expected_version"*) ;;
  *)
    printf '%s\n' "unexpected synergy-core version output: $version_output" >&2
    exit 1
    ;;
esac

help_output=$("$binary" --help)
case "$help_output" in
  *"Usage: synergy-core <server | client>"*) ;;
  *)
    printf '%s\n' "unexpected synergy-core help output: $help_output" >&2
    exit 1
    ;;
esac

printf '%s\n' "synergy-core consumer checks passed"
