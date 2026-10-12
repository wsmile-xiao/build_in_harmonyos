#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-iemlib 1.22.3.
#
# Part A - five iemlib classes driven directly (7 assertions):
#   [db2v 0]                          -> 1      (exp(0.11512925465 * 0) == 1)
#   [v2db 1]                          -> 0      (8.6858896381 * log(1) == 0)
#   [split 0] with -3                 -> left outlet  (f < threshold)
#   [split 0] with 3                  -> right outlet (f >= threshold)
#   [modulo_counter 3 0] + 4 bangs    -> 0 1 2 0 (wraps at x_max)
#   plus the library load banner.
#
# NOTE: an earlier revision of this test drove [wrap 1.5] / [wrap -1.5].
# Reverse-destruction (L1e, see notes.md) showed those two assertions kept
# passing with iemlib.pd_linux replaced by a 0-byte stub, i.e. they were
# being answered by Pd's own builtin [wrap] and never touched iemlib at
# all. They are replaced here by [split] / [modulo_counter], which are
# registered only by src/iemlib.c.
#
# Part B - end-to-end consumer flow through the *packaged abstractions*
# [dbtofad] and [fadtodb] (installed from abs/ into lib/pd-externals).
# Each of them is a real iemlib pipeline: it feeds its own breakpoint
# table into the iemlib C object [transf_fader] and interpolates on it.
#   MIDI-dB 40 --[dbtofad]--> fader-scale 6 --[fadtodb]--> MIDI-dB 40
# The two breakpoints 0->0 and 40->6 (resp. 6->40) are taken verbatim
# from upstream abs/dbtofad.pd, so the round trip is exact by
# construction, not by fitting to whatever came out.
#
# Part C - anti-false-green guards (3 assertions). A Pd external that
# failed to load still lets its (already created) objects answer some
# messages, so the prints above can be read as green while the classes
# were never built. These guards make "couldn't create"/"unknown
# function"/any unexpected "error:" line a hard failure. The one allowed
# family of lines is Pd's own *registration*-time notice
#   error: class <name>: sorry: only 5 creation args allowed
# printed once per class whose creator declares more than MAXPDARG (=5)
# argument types (pd 0.54 src/m_class.c, class_addcreator()). Pd only
# stops type-checking the surplus arguments -- the class still registers
# and object creation works, which the log below proves (the load banner
# and every functional check pass). How many of these lines appear is a
# property of the build and not of this test: an earlier local build
# printed one, CI build #84535 printed twelve. So the notice itself is
# matched, not a single hard-coded class name; every *other* "error:"
# line still fails the check.
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed iemlib.pd_linux + patches
#   PATCH    path to test_pd_iemlib.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_iemlib.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/iemlib.pd_linux" ] || { echo "FAIL: iemlib.pd_linux missing"; exit 1; }
[ -f "$EXT_DIR/help/db2v-help.pd" ] || { echo "FAIL: help patch missing"; exit 1; }
# Part B drives these two *packaged* abstractions; without them the
# round trip cannot run, and a stale local copy could silently stand in.
[ -f "$EXT_DIR/dbtofad.pd" ] || { echo "FAIL: dbtofad.pd not packaged: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/fadtodb.pd" ] || { echo "FAIL: fadtodb.pd not packaged: $EXT_DIR"; exit 1; }

WORK="${TMPDIR:-.}/pd-iemlib-test.$$"
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

CHECKS=0
fails=0
check() {
    CHECKS=$((CHECKS + 1))
    if grep -q "$1" "$LOG"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2 (expected '$1')"
        fails=$((fails + 1))
    fi
}
check_absent() {
    CHECKS=$((CHECKS + 1))
    if grep -q "$1" "$LOG"; then
        echo "FAIL: $2 (forbidden '$1' in pd output)"
        fails=$((fails + 1))
    else
        echo "PASS: $2"
    fi
}
check_count() {
    CHECKS=$((CHECKS + 1))
    _n=$(grep -c "$1" "$LOG" || true)
    if [ "$_n" -eq "$2" ]; then
        echo "PASS: $3"
    else
        echo "FAIL: $3 (expected '$1' x$2, got x$_n)"
        fails=$((fails + 1))
    fi
}

# --- Part A: direct object calls (7) ---
check "iemlib (1.22-1) library loaded" "iemlib.pd_linux loaded by Pd"
check "IEM_DB2V: 1" "iemlib [db2v 0] -> 1"
check "IEM_V2DB: 0" "iemlib [v2db 1] -> 0"
check "IEM_SPLIT_LT: -3" "iemlib [split 0] -3 -> less-than outlet"
check "IEM_SPLIT_GE: 3" "iemlib [split 0] 3 -> greater-equal outlet"
check "IEM_MODULO: 2" "iemlib [modulo_counter 3 0] counts up to 2"
check_count '^IEM_MODULO: 0$' 2 "iemlib [modulo_counter 3 0] wraps 0 1 2 0"

# --- Part B: packaged abstractions, end-to-end round trip (2) ---
check "IEM_DBFAD: 6" "[dbtofad] MIDI-dB 40 -> fader-scale 6 (transf_fader breakpoints)"
check "IEM_FADDB: 40" "[fadtodb] fader-scale 6 -> MIDI-dB 40 (round trip back)"

# --- Part C: anti-false-green guards (3) ---
check_absent "couldn't create" "no Pd object failed to instantiate"
check_absent "unknown function" "no unknown Pd message/function name"
# Pd prints this notice once per class whose creator declares more than
# MAXPDARG (=5) argument types (pd 0.54 src/m_class.c, class_addcreator()):
# Pd only stops type-checking the surplus args, the class still registers
# and works. The number of such classes is a property of the built library
# (1 in an earlier local build, 12 on the CI worker for build #84535), so
# the notice is matched by pattern and any other "error:" line still fails.
KNOWN_PD_NOTICE='^error: (class [^:]*|unnamed class): sorry: only 5 creation args allowed$'
ALL_ERRORS=$(grep -c '^error: ' "$LOG" || true)
KNOWN_ERRORS=$(grep -cE "$KNOWN_PD_NOTICE" "$LOG" || true)
CHECKS=$((CHECKS + 1))
if [ "$ALL_ERRORS" -eq "$KNOWN_ERRORS" ]; then
    echo "PASS: no unexpected Pd error line ($ALL_ERRORS/$ALL_ERRORS are Pd's class-creation-args notice)"
else
    echo "FAIL: unexpected Pd error line(s): $(grep '^error: ' "$LOG" | grep -vcE "$KNOWN_PD_NOTICE" || true)"
    fails=$((fails + 1))
fi

echo "IEMLIB_CHECK_SUMMARY checks=$CHECKS fails=$fails"
[ "$fails" -eq 0 ]