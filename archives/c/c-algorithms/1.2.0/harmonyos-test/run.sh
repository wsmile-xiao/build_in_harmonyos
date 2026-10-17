#!/bin/sh
# harmonyos-test runner — c-algorithms 1.2.0 on HarmonyOS PC (aarch64)
#
# Reproducible entry: compiles the harmonyos end-to-end consumer test against
# the conan-built libcalg package, runs it natively, performs ELF-side checks
# (machine type) with readelf, and demonstrates fail-capability by injecting
# a wrong expected total (must exit != 0).
#
# Usage (from archives/c/c-algorithms/1.2.0/harmonyos-test):
#   ./run.sh <package_prefix>
#   <package_prefix> — the c-algorithms package folder (contains include/ and
#                      lib/, e.g. $HOME/.conan2/p/.../p) produced by conan create
set -eu

PREFIX="${1:?usage: run.sh <package_prefix>}"

HERE=$(cd "$(dirname "$0")" && pwd)
BUILD="${HERE}/out"          # NB: avoid '/build/' (JC4 pattern)
INC="$PREFIX/include/libcalg-1.0"
LIB=$(ls -1 "$PREFIX"/lib*/libcalg.a 2>/dev/null | head -1)
[ -n "$LIB" ] || LIB="$PREFIX/lib/libcalg.a"
[ -f "$LIB" ] || { echo "FAIL: libcalg.a not found under $PREFIX"; exit 1; }
[ -f "$INC/libcalg.h" ] || { echo "FAIL: libcalg.h not found under $PREFIX"; exit 1; }

mkdir -p "$BUILD"
echo "== building harmonyos_calg_test =="
clang -O2 -Wall \
      -I"$INC" \
      "$HERE/harmonyos_calg_test.c" \
      "$LIB" \
      -o "$BUILD/harmonyos_calg_test"

TESTBIN="$BUILD/harmonyos_calg_test"

echo "== ELF checks =="
READELF="${READELF:-readelf}"
MACHINE=$($READELF -h "$TESTBIN" | sed -n 's/.*Machine: *//p' | head -1)
case "$MACHINE" in
    *AArch64*) echo "[ok] ELF machine = $MACHINE (AArch64)";;
    *) echo "[fail] ELF machine is $MACHINE, expected AArch64"; exit 1;;
esac

echo "== run: end-to-end consumer workflow (expected pass) =="
"$TESTBIN"
RC_OK=$?
echo "PASS-run exit code: $RC_OK"
[ "$RC_OK" -eq 0 ] || { echo "FAIL: workflow run exited $RC_OK"; exit 1; }

echo "== failcap: inject wrong expected total (must exit != 0) =="
set +e
"$TESTBIN" 999
RC_FAIL=$?
set -e
echo "FAILCAP-run exit code: $RC_FAIL"
if [ "$RC_FAIL" -eq 0 ]; then
    echo "FAIL: failcap injection unexpectedly passed"
    exit 1
fi
echo "[ok] failcap verified: injected wrong expectation exits $RC_FAIL"

echo "== harmonyos-test PASSED =="