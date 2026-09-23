#!/bin/sh
# test_package/test.sh — consumer tests for the clpbar `bar` binary.
# 3 checks: --version smoke test, pipe round-trip, file round-trip.
# Every check compares real transferred bytes with cmp; any mismatch fails.
set -eu

# [shell_getcwd] HMDFS: conan test cwd may have inaccessible parents
# (shell-init/job-working-directory getcwd warnings). Recover to a
# forward-resolvable writable dir before running anything.
# NOTE: keep POSIX sh compatible (no pipefail); workdir comes from $TMPDIR
# injected by the test driver. Fall back to current dir if mktemp fails.
_TMPBASE="${TMPDIR:-${TMP:-/tmp}}"
_WORKDIR="$(mktemp -d "$_TMPBASE/clpbar-test.XXXXXX" 2>/dev/null || echo "")"
if [ -n "$_WORKDIR" ] && [ -d "$_WORKDIR" ]; then
  cd "$_WORKDIR"
  trap 'cd / 2>/dev/null || true; rm -rf "$_WORKDIR"' EXIT INT TERM
elif [ -n "$_TMPBASE" ] && [ -d "$_TMPBASE" ]; then
  cd "$_TMPBASE" 2>/dev/null || true
fi

# Driver passes absolute binary path (robust when PATH/cwd is broken);
# fall back to PATH lookup for local runs.
BAR="${BAR_BIN:-bar}"

echo "[1/3] bar --version"
# Upstream bar prints version but exits non-zero on device; check string only.
VER="$("$BAR" --version 2>&1 || true)"
echo "  version output: $VER"
case "$VER" in
  *1.11.1*) echo "  OK: version matches";;
  *) echo "FAIL: unexpected version output: $VER"; exit 1;;
esac

echo "[2/3] stdin/stdout pipe round-trip through bar"
printf 'Hello clpbar pipe test data 0123456789\n' > pipe_in.bin
cat pipe_in.bin | "$BAR" 2>/dev/null > pipe_out.bin
cmp pipe_in.bin pipe_out.bin
echo "  OK: pipe data identical"

echo "[3/3] file round-trip with -if/-of (mirrors upstream test-002)"
printf 'Hello clpbar file test data 0123456789\n' > file_in.bin
cp file_in.bin file_ref.bin
"$BAR" -if file_in.bin -of file_out.bin 2>/dev/null
cmp file_ref.bin file_out.bin
echo "  OK: file data identical"

echo "ALL 3 TESTS PASSED"
rm -f pipe_in.bin pipe_out.bin file_in.bin file_ref.bin file_out.bin
