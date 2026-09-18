#!/bin/sh
# test_libbf.sh — compile test_libbf.c against the packaged libbf and run it.
# Usage: test_libbf.sh <package_include_dir> <package_lib_dir>
# The C program prints TAP-style "ok / not ok" lines for its 5 real checks
# and exits non-zero on any failure, so a silent skip is impossible.
#
# Read-only /tmp guard: this shell creates a temp file in /tmp for every
# command substitution $(...)/backticks and pipe. /tmp is read-only on the
# runner, so this script uses no $(), no backticks and no pipes — only
# POSIX parameter expansion and redirections. Compiler temp files honor
# the exported TMPDIR/TMP/TEMP (injected by the recipe to a writable dir).
set -eu

PKG_INCLUDE="$1"
PKG_LIB="$2"

# Writable temp root for the toolchain. ${VAR:-} expansion needs no fork
# and no /tmp. Default to the current (writable) directory when unset.
if [ -z "${TMPDIR:-}" ]; then
  TMPDIR="."
  export TMPDIR
else
  export TMPDIR
fi
if [ -z "${TMP:-}" ]; then
  TMP="$TMPDIR"
  export TMP
fi
if [ -z "${TEMP:-}" ]; then
  TEMP="$TMPDIR"
  export TEMP
fi

CC_BIN="${CC:-clang}"
# Profile may pin an absolute compiler path absent on this runner.
# Strip the directory with ${var##*/} (pure expansion, no subprocess) and
# let /bin/sh resolve the basename via the injected conan PATH at exec time.
case "$CC_BIN" in
  */*)
    if [ ! -x "$CC_BIN" ]; then
      CC_BIN="${CC_BIN##*/}"
    fi
    ;;
esac

"$CC_BIN" -O2 -I"$PKG_INCLUDE" test_libbf.c "$PKG_LIB/libbf.a" -lm -o test_libbf
./test_libbf
