#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-osc 0.3.1.
#
# Loads the installed osc externals with the OHOS `pd` (from the
# puredata package) and checks one OSC round trip:
#   [packOSC]   "/ping 1 2" -> big-endian byte list
#                "/ping"      = 47 112 105 110 103 0 0 0
#                typetags ",ii" = 44 105 105 0
#                int32 1       = 0 0 0 1
#                int32 2       = 0 0 0 2
#   [unpackOSC] byte list     -> "/ping 1 2"  (exact round trip)
#   [routeOSC]  "/ping 1 2"   -> "/ping 1 2" on the catch-all outlet
#                                (no method is registered, so the whole
#                                 message falls through to the last outlet)
# and asserts that Pd reported no failed class creation.
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_osc.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_osc.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
for blob in packOSC unpackOSC routeOSC pipelist; do
    [ -f "$EXT_DIR/$blob.pd_linux" ] || { echo "FAIL: $blob.pd_linux missing"; exit 1; }
done

WORK="${TMPDIR:-.}/pd-osc-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

LOG="$WORK/pd.log"
if command -v timeout >/dev/null 2>&1; then
    timeout 60 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
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

check "PDOSC_BYTES: 47 112 105 110 103 0 0 0 44 105 105 0 0 0 0 1 0 0 0 2" \
      "pd-osc [packOSC] packs /ping 1 2 as an OSC message"
check "PDOSC_RT: /ping 1 2" \
      "pd-osc [unpackOSC] decodes it back to the original Pd message"
check "PDOSC_ROUTED: /ping 1 2" \
      "pd-osc [routeOSC] hands the unmatched message to its catch-all outlet"
if grep -q "couldn't create\|couldn't find" "$LOG"; then
    echo "FAIL: Pd reported a class that could not be created/loaded"
    grep "couldn't create\|couldn't find" "$LOG" || true
    fails=$((fails + 1))
else
    echo "PASS: every class in the patch was created by Pd"
fi

echo "PDOSC_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]