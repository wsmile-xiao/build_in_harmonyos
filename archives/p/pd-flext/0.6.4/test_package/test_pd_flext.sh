#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-flext 0.6.4.
#
# Loads a flext-built external (compiled by test_package/conanfile.py against
# the installed pd-flext package) with the OHOS `pd` from the puredata package
# and drives it headlessly:
#   [flextest 100] construction       -> FLEXT_TEST_INIT: 100
#   float 5 into it (100 + 5)         -> FLEXT_TEST_RESULT: 105
#   result to [print]                 -> FLEXT_TEST: 105
#
# Env:
#   PD_BIN        path to the installed `pd` executable
#   EXT_DIR       directory holding the built flextest.pd_linux
#   PATCH         path to test_pd_flext.pd
#   FLEXT_LIBDIR  directory holding libflext-pd.so (for the runtime loader)
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the external dir}"
PATCH="${PATCH:?PATCH must point to test_pd_flext.pd}"
FLEXT_LIBDIR="${FLEXT_LIBDIR:?FLEXT_LIBDIR must point to the pd-flext libdir}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -f "$EXT_DIR/flextest.pd_linux" ] || { echo "FAIL: flextest.pd_linux missing"; exit 1; }
[ -f "$FLEXT_LIBDIR/libflext-pd.so.0.6" ] || { echo "FAIL: libflext-pd.so.0.6 missing"; exit 1; }

WORK="${TMPDIR:-.}/pd-flext-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

LD_LIBRARY_PATH="$FLEXT_LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH

LOG="$WORK/pd.log"
if command -v timeout >/dev/null 2>&1; then
    timeout 20 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
else
    "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
fi

echo "--- pd output ---"
cat "$LOG"
echo "--- end pd output ---"

fails=0
check() {
    if grep -q "$1" "$LOG"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2 (expected '$1')"
        fails=$((fails + 1))
    fi
}

check "FLEXT_TEST_INIT: 100"   "flext external constructed ([flextest 100])"
check "FLEXT_TEST_RESULT: 105" "flext method arg+float (100+5) executed"
check "FLEXT_TEST: 105"        "flext outlet delivered to [print]"

echo "FLEXT_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
