#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-maxlib 1.6.0.
#
# Loads the installed maxlib externals with the OHOS `pd` (from the
# puredata package) and drives two deterministic classes:
#   [divide 10 20] -> 0.5
#   [plus 3 4]     -> 7
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_maxlib.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_maxlib.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/divide.pd_linux" ] || { echo "FAIL: divide.pd_linux missing"; exit 1; }

WORK="${TMPDIR:-.}/pd-maxlib-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

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

check "MAXLIB_DIVIDE: 0.5" "maxlib [divide 10 20] -> 0.5"
check "MAXLIB_PLUS: 7" "maxlib [plus 3 4] -> 7"

echo "MAXLIB_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
