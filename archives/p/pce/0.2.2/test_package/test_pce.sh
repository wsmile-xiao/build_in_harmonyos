#!/bin/sh
# test_package/test_pce.sh — consumer smoke test for the pce emulator suite.
# Invoked as: sh test_pce.sh <package-bin-dir>
# Runs in conanrun env. Prints PASS/FAIL per case plus a final
# "RESULT: N passed, M failed" line parsed by test_package/conanfile.py
# into the HMBS_TEST_PACKAGE_RESULT marker (discovered/passedCount).
set -eu

BIN_DIR="${1:?usage: test_pce.sh <package-bin-dir>}"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
}

echo "[test] pce bin dir: $BIN_DIR"

for prog in pce-ibmpc pce-macplus pce-rc759 pce-sim405 pce-sim6502 pce-simarm pce-sims32; do
    BIN="$BIN_DIR/$prog"
    if [ ! -x "$BIN" ]; then
        bad "$prog missing or not executable ($BIN)"
        continue
    fi
    # 1. Version flag: ibmpc/macplus/rc759 use -V (pce_getopt), the
    # sim* family only understands --version (see src/arch/sim*/main.c
    # at 0.2.2: argc==2 --help/--version, "-V" is "unknown option").
    # Try -V first, fall back to --version; both must print 0.2.2.
    OUT=""
    if OUT="$("$BIN" -V 2>&1)"; then
        case "$OUT" in
            *"0.2.2"*) ok "$prog version prints 0.2.2 ($BIN -V)" ;;
            *) bad "$prog -V missing 0.2.2 (got: $OUT)" ;;
        esac
    elif OUT="$("$BIN" --version 2>&1)"; then
        case "$OUT" in
            *"0.2.2"*) ok "$prog version prints 0.2.2 ($BIN --version)" ;;
            *) bad "$prog --version missing 0.2.2 (got: $OUT)" ;;
        esac
    else
        bad "$prog version flag exited non-zero"
    fi
    # 2. Help flag: must exit 0 and print usage.
    if OUT="$("$BIN" --help 2>&1)"; then
        case "$OUT" in
            *"usage:"*) ok "$prog --help prints usage" ;;
            *) bad "$prog --help missing usage (got: $OUT)" ;;
        esac
    else
        bad "$prog --help exited non-zero"
    fi
done

echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    echo "test_package FAILED"
    exit 1
fi
echo "test_package PASSED"
