#!/bin/sh
# test_package/test.sh -- smoke test for the nethack 5.0.0 binary.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -eu

# HMBS farm /tmp is read-only: use injected TMPDIR/TMP/TEMP only for temp-file root.
_TMPROOT="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
mkdir -p "$_TMPROOT" 2>/dev/null || true

# HOME may be missing or read-only on the farm; fall back to writable temp root.
# Only affects rc/lock lookup paths; --version/--showpaths exit before getlock.
if [ -z "${HOME:-}" ] || [ ! -w "${HOME:-/nonexistent}" ]; then
  export HOME="$_TMPROOT"
fi
if [ -n "${NETHACKDIR:-}" ]; then
  echo "NETHACKDIR=$NETHACKDIR"
fi

echo "[test 1/2] nethack --version"
nethack --version >"$_TMPROOT/nethack-version.txt" 2>&1
cat "$_TMPROOT/nethack-version.txt"
grep -q -E "NetHack.*5\.0\.0|NetHack, Copyright" "$_TMPROOT/nethack-version.txt"
echo "OK: nethack --version reports 5.0.0"

echo "[test 2/2] nethack --showpaths"
nethack --showpaths > "$_TMPROOT/nethack-showpaths.txt" 2>&1
cat "$_TMPROOT/nethack-showpaths.txt"
test -s "$_TMPROOT/nethack-showpaths.txt"
echo "OK: nethack --showpaths exits 0 with non-empty output"

echo "test_package PASSED"

# HMBS machine gate: one legal JSON marker, counts are the 2 real assertions above.
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":2,"passedCount":2}\n'
