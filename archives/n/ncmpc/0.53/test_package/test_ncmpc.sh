#!/usr/bin/env bash
set -eu

command -v ncmpc >/dev/null 2>&1
version_output="$(ncmpc --version)"
printf '%s\n' "$version_output"

case "$version_output" in
  *"ncmpc version: 0.53"*) ;;
  *)
    printf 'unexpected ncmpc version output\n' >&2
    exit 1
    ;;
esac

case "$version_output" in
  *"wide"*) ;;
  *)
    printf 'wide-character ncurses support is missing\n' >&2
    exit 1
    ;;
esac
