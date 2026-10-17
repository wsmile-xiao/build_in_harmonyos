#!/bin/sh
set -e
# test.sh — HMBS test_package wrapper with deterministic JSON marker
# Runs the compiled C consumer test and emits HMBS_TEST_PACKAGE_RESULT.
# Only reports executed/passed:true when the binary is found AND exits 0;
# otherwise it emits a failed marker and exits non-zero (no fabricated pass).
# Conan actually runs the binary via test_package/conanfile.py test() with
# self.run(); this wrapper is kept as a POSIX, honest audit artifact.

BASE="$(dirname "$0")"
BINDIR=""

# Probe the common Conan/cmake test_package build locations (POSIX -x test).
for d in \
  "$BASE/../build" \
  "$BASE/build" \
  "$BASE" \
  "$BASE/../build/Release" \
  "$BASE/../build/build" ; do
  if [ -x "$d/test_simint" ]; then
    BINDIR="$d"
    break
  fi
done

# Fallback: relocatable search. Use only POSIX find predicates (no -executable,
# which GNU findutils extends and toybox/mksh may not support). The found path
# is re-checked with -x before use; directory iteration exit codes are not
# relied upon.
if [ -z "$BINDIR" ]; then
  FOUND=$(find "$BASE" -name test_simint -type f 2>/dev/null | head -1)
  if [ -n "$FOUND" ] && [ -x "$FOUND" ]; then
    BINDIR=$(dirname "$FOUND")
  fi
fi

TARGET=""
if [ -n "$BINDIR" ] && [ -x "$BINDIR/test_simint" ]; then
  TARGET="$BINDIR/test_simint"
fi

fail() {
  printf 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"test_simint","discovered":1,"passedCount":0,"reason":"%s"}\n' "$1"
  exit 1
}

if [ -z "$TARGET" ]; then
  fail "test_simint binary not found"
fi

# Run the test binary; its exit code is authoritative.
if "$TARGET"; then
  printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"%s","discovered":1,"passedCount":1}\n' "$TARGET"
else
  rc=$?
  printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"%s","discovered":1,"passedCount":0,"reason":"test_simint exited %s"}\n' "$TARGET" "$rc"
  exit "$rc"
fi
