#!/bin/bash
# Consumer test for the packaged inputlircd (R34: it executes the real binary).
# Every product assertion pins BOTH an exit status and the exact upstream diagnostic,
# so a behaviour change flips it to [FAIL]; counters move only inside ck()/ckf().
# The compiled socket probe is a PLATFORM OBSERVATION (obs(), "[OBSERVE]" prefix,
# OBSERVATIONS_* counters): it neither runs nor links inputlircd, so per the W4 r1
# verdict it is deliberately NOT counted in ASSERTIONS_*.
set -u
BIN="${1:-inputlircd}"
PROBE="${2:-}"

# Never trust the inherited cwd: Conan may run this from a folder it recycles.
WORK="${TMPDIR:-$HOME/tmp}/il34-tp-$$"
mkdir -p "$WORK" || { echo "cannot create scratch dir $WORK"; exit 1; }
cd "$WORK" || exit 1

TOTAL=0; OK=0; FAILED=""; OBS_TOTAL=0; OBS_OK=0

ck() {  # ck <name> <expected-rc> <expected-substring> <cmd...>
  local name="$1" want="$2" needle="$3"; shift 3
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  TOTAL=$((TOTAL+1))
  if [ "$rc" = "$want" ] && printf '%s' "$out" | grep -qF -- "$needle"; then
    OK=$((OK+1)); echo "[PASS] $name (rc=$rc, matched: $needle)"
  else
    FAILED="$FAILED\n  - $name: want rc=$want + '$needle', got rc=$rc; out<<$out>>"
    echo "[FAIL] $name (want rc=$want + '$needle', got rc=$rc)"
  fi
}
ckf() {  # ckf <name> <file> <needle>
  local name="$1" file="$2" needle="$3"
  TOTAL=$((TOTAL+1))
  if [ -f "$file" ] && grep -qF -- "$needle" "$file"; then
    OK=$((OK+1)); echo "[PASS] $name"
  else
    FAILED="$FAILED\n  - $name: $file missing or lacks '$needle'"
    echo "[FAIL] $name ($file)"
  fi
}
obs() {  # obs <name> <expected-rc> <expected-substring> <cmd...>  (NOT counted)
  local name="$1" want="$2" needle="$3"; shift 3
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  OBS_TOTAL=$((OBS_TOTAL+1))
  if [ "$rc" = "$want" ] && printf '%s' "$out" | grep -qF -- "$needle"; then
    OBS_OK=$((OBS_OK+1)); echo "[OBSERVE] $name (not counted; rc=$rc, matched: $needle)"
  else
    echo "[OBSERVE-DIVERGED] $name (not counted; want rc=$want + '$needle', got rc=$rc)"
  fi
}

echo "### binary under test: $BIN"

# --- A: packaging and CLI surface --------------------------------------------
TOTAL=$((TOTAL+1))
if [ -x "$BIN" ] || command -v "$BIN" >/dev/null 2>&1; then
  OK=$((OK+1)); echo "[PASS] A1 packaged binary present and executable"
else
  FAILED="$FAILED\n  - A1 $BIN not executable"; echo "[FAIL] A1"
fi
ck "A2 unknown option rejected with EX_USAGE" 64 "Unknown option!" "$BIN" -h
ck "A3 bare invocation rejected with EX_USAGE" 64 "Not enough arguments." "$BIN"

# --- B: evdev input surface (Wall 1: EACCES on the node, GLOB_NOMATCH on the dir)
ck "B1 -n finds no evdev node for this uid" 71 "No event devices found!" \
   "$BIN" -f -d "$WORK/l1.sock" -n "*"
ck "B2 explicit evdev node refused by DAC, daemon refuses to start" 71 \
   "Unable to open any event device!" "$BIN" -f -d "$WORK/l2.sock" /dev/input/event0

# --- O: AF_UNIX output surface (Wall 3) -- PLATFORM OBSERVATION, not an assertion.
# The probe neither executes nor links inputlircd (W4 r1: 不得计入 assertion_count).
# A missing probe is a hard error, never a silent skip.
if [ -z "$PROBE" ] || [ ! -x "$PROBE" ]; then
  echo "ERROR: platform observation probe missing or not executable: '$PROBE'"
  exit 1
fi
obs "O1 filesystem unix bind EPERM while abstract namespace binds" 0 \
    "VERDICT: filesystem unix-socket bind refused" "$PROBE" "$WORK" 

# --- D: startup ordering ------------------------------------------------------
# main() opens the event devices before it touches the socket or drops
# privileges, so a bogus drop-target user must still die on the evdev step.
# Falsifiable: if upstream reorders, the matched diagnostic changes.
ck "D1 evdev open dominates before user resolution and socket setup" 71 \
   "Unable to open any event device!" \
   "$BIN" -f -d "$WORK/l4.sock" -u nosuchil34user -n "*"

# --- E: installed layout ------------------------------------------------------
PREFIX="$(dirname "$(cd "$(dirname "$BIN")" >/dev/null 2>&1 && pwd)")"
ckf "E1 man page installed under share/man/man8" \
    "$PREFIX/share/man/man8/inputlircd.8" "inputlircd"
ckf "E2 systemd unit shipped for Linux callers" \
    "$PREFIX/lib/systemd/system/inputlirc.service" "inputlircd"

echo "ASSERTIONS_TOTAL=$TOTAL"
echo "ASSERTIONS_PASS=$OK"
echo "ASSERTIONS_FAIL=$((TOTAL-OK))"
echo "OBSERVATIONS_TOTAL=$OBS_TOTAL"
echo "OBSERVATIONS_MATCH=$OBS_OK"
cd /
rm -rf "$WORK" 2>/dev/null
if [ "$OK" != "$TOTAL" ]; then printf 'Failures:%b\n' "$FAILED"; exit 1; fi
if [ "$TOTAL" -lt 8 ]; then echo "ERROR: only $TOTAL assertions ran (floor is 8)"; exit 1; fi
exit 0
