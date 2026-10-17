#!/bin/sh
#--------------------------------------------------------------------
# HarmonyOS consumer use case for pd-iemlib 1.22.3.
#
# This script demonstrates a complete end-to-end consumer flow on OHOS:
# it loads the packaged iemlib library and drives the dbtofad/fadtodb
# abstraction round trip (MIDI-dB 40 <-> fader-scale 6).
#
# This is a HarmonyOS-specific consumer test (鸿蒙特有消费者用例).
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_consumer.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/iemlib.pd_linux" ] || { echo "FAIL: iemlib.pd_linux missing"; exit 1; }
[ -f "$EXT_DIR/dbtofad.pd" ] || { echo "FAIL: dbtofad.pd not packaged: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/fadtodb.pd" ] || { echo "FAIL: fadtodb.pd not packaged: $EXT_DIR"; exit 1; }

WORK="${TMPDIR:-.}/pd-iemlib-consumer.$$"
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
check_absent() {
    if grep -q "$1" "$LOG"; then
        echo "FAIL: $2 (forbidden '$1' in pd output)"
        fails=$((fails + 1))
    else
        echo "PASS: $2"
    fi
}

# HarmonyOS consumer use case: MIDI-dB 40 -> fader-scale 6 -> MIDI-dB 40
check "IEM_DBFAD: 6" "consumer [dbtofad] MIDI-dB 40 -> fader-scale 6"
check "IEM_FADDB: 40" "consumer [fadtodb] fader-scale 6 -> MIDI-dB 40 (round trip)"

# Guards
check_absent "couldn't create" "no Pd object failed to instantiate"
check_absent "unknown function" "no unknown Pd message/function name"

echo "CONSUMER_USE_CASE_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]