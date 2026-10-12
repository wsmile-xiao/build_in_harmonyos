#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-ggee 0.28.
#
# Loads the installed ggee externals with the OHOS `pd` (from the
# puredata package) and drives three deterministic control classes:
#   [constant pi] (bang) -> 3.14159
#   [sinh 2]             -> 3.62686
#   [inv 10]             -> 0.1
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_ggee.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_ggee.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
for cls in constant sinh inv; do
    [ -f "$EXT_DIR/$cls.pd_linux" ] || { echo "FAIL: $cls.pd_linux missing"; exit 1; }
done
# The library ships 42 classes; refuse to run against a truncated install.
n_ext=$(ls "$EXT_DIR"/*.pd_linux 2>/dev/null | wc -l)
[ "$n_ext" -eq 42 ] || { echo "FAIL: expected 42 externals, found $n_ext"; exit 1; }

WORK="${TMPDIR:-.}/pd-ggee-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

LOG="$WORK/pd.log"
# WSL/qemu reproduction env (binfmt + /opt/ohos-guest musl) lacks the OHOS
# fortify symbol __fd_chk that the CI-built `pd` was linked against.  When the
# guest-side empty-implementation shim exists, preload it for the `pd` process
# only (never export globally: x86 subprocesses would spew "cannot be
# preloaded" noise).  On CI's native OHOS the path does not exist and the
# identical direct-call branch is taken; the shim exports exactly one symbol,
# computes nothing and prints nothing, so check outcomes are unaffected.
FDCHK_SHIM=/opt/ohos-guest/lib/libfdchkshim.so
run_pd() {
    if [ -f "$FDCHK_SHIM" ]; then
        LD_PRELOAD="$FDCHK_SHIM" "$@"
    else
        "$@"
    fi
}
if command -v timeout >/dev/null 2>&1; then
    run_pd timeout 40 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
else
    run_pd "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
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

check "GGEE_CONSTANT: 3.14159" "ggee [constant pi] (bang) -> 3.14159"
check "GGEE_SINH: 3.62686" "ggee [sinh 2] -> 3.62686"
check "GGEE_INV: 0.1" "ggee [inv 10] -> 0.1"

echo "GGEE_CHECK_SUMMARY fails=$fails externals=$n_ext"
[ "$fails" -eq 0 ]
