#!/bin/sh
set -eu

tio_bin="$1"

version_output="$("$tio_bin" --version)"
case "$version_output" in
  "tio 3.9"*) ;;
  *)
    echo "unexpected version output: $version_output" >&2
    exit 1
    ;;
esac

help_output="$("$tio_bin" --help)"
case "$help_output" in
  *"Usage: tio [<options>] <tty-device|profile|tid>"*) ;;
  *)
    echo "help output missing usage banner" >&2
    exit 1
    ;;
esac

"$tio_bin" --list >/dev/null
