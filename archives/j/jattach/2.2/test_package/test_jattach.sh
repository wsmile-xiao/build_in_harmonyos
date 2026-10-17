#!/usr/bin/env bash
# test_jattach.sh — consumer tests for the packaged jattach binary (R34).
#
# Drives the installed CLI and asserts observable behaviour:
#   1) usage/version banner, exit codes and PID validation
#   2) /proc-based lookup of a missing process
#   3) HotSpot attach trigger path against a live dummy
#      process: the .attach_pid<PID> trigger file is observed while jattach
#      polls for the JVM attach socket, SIGQUIT is delivered, the failure is
#      reported and the trigger file is cleaned up
#   4) the packaged artifact is an AArch64 ELF executable
#
# Note: HarmonyOS HMMAC denies AF_UNIX pathname socket creation for non-app
# processes (EPERM), so the "Connected to remote JVM" positive path cannot
# be exercised on-device; the trigger/signal mechanism is asserted instead.

set -euo pipefail

if ! JATTACH_BIN="$(command -v jattach)"; then
    echo "        [fail] jattach not found in PATH"
    exit 1
fi

WORK_DIR="$(pwd)/jattach-test.$$"
mkdir -p "$WORK_DIR/jattach-tmp"
cd "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0

pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "        [ok] $1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "        [fail] $1"; }

assert_eq() {  # desc expected actual
    if [ "$3" = "$2" ]; then
        pass "$1 (=$3)"
    else
        fail "$1 (expected $2, got $3)"
    fi
}

assert_contains() {  # desc haystack needle
    case "$2" in
        *"$3"*) pass "$1" ;;
        *) fail "$1 (missing: $3)" ;;
    esac
}

assert_absent() {  # desc path
    if [ ! -e "$2" ]; then
        pass "$1"
    else
        fail "$1 (still present: $2)"
    fi
}

echo "[step] jattach consumer tests"

if [ -x "$JATTACH_BIN" ]; then
    pass "binary installed and executable"
else
    fail "binary installed and executable"
fi

# ── CLI contract ────────────────────────────────────────────────────────────
RC=0
USAGE_OUT="$("$JATTACH_BIN" 2>/dev/null)" || RC=$?
assert_eq "no-argument invocation exits 1" 1 "$RC"
assert_contains "version banner printed" "$USAGE_OUT" "jattach 2.2"
assert_contains "usage line printed" "$USAGE_OUT" "Usage: jattach <pid> <cmd>"

ALL_COMMANDS=1
for CMD in load threaddump dumpheap setflag properties jcmd inspectheap datadump printflag agentProperties; do
    case "$USAGE_OUT" in
        *"$CMD"*) ;;
        *) ALL_COMMANDS=0 ;;
    esac
done
assert_eq "all 10 documented commands listed" 1 "$ALL_COMMANDS"

RC=0
ERR="$("$JATTACH_BIN" abc properties 2>&1 >/dev/null)" || RC=$?
assert_eq "non-numeric PID rejected (rc)" 1 "$RC"
assert_contains "non-numeric PID diagnostic" "$ERR" "abc is not a valid process ID"

RC=0
ERR="$("$JATTACH_BIN" 0 properties 2>&1 >/dev/null)" || RC=$?
assert_eq "PID 0 rejected (rc)" 1 "$RC"
assert_contains "PID 0 diagnostic" "$ERR" "0 is not a valid process ID"

RC=0
ERR="$("$JATTACH_BIN" 99999999 properties 2>&1 >/dev/null)" || RC=$?
assert_eq "missing process exits 1" 1 "$RC"
assert_contains "missing process diagnostic" "$ERR" "Process 99999999 not found"

# ── HotSpot attach trigger path ─────────────────────────────────────────────
# jattach creates .attach_pid<PID> next to the target (target cwd, or the
# JATTACH_PATH tmp dir as fallback), sends SIGQUIT, then polls ~0.5 s for
# the JVM attach socket.  Both trigger locations are watched.
# The dummy target is a Python process with a SIGQUIT handler: unlike POSIX
# shells (which ignore SIGQUIT in background jobs), it can prove delivery by
# exiting with code 7 from the handler.
TARGET_READY="$WORK_DIR/target-ready"
python3 -c '
import signal, sys, time

def handler(signum, frame):
    sys.exit(7)

signal.signal(signal.SIGQUIT, handler)
open(sys.argv[1], "w").write("ready")
time.sleep(30)
' "$TARGET_READY" &
TARGET_PID=$!
TRIGGER_CWD="$WORK_DIR/.attach_pid$TARGET_PID"
TRIGGER_TMP="$WORK_DIR/jattach-tmp/.attach_pid$TARGET_PID"

# barrier: make sure the SIGQUIT handler is installed before jattach fires
python3 - "$TARGET_READY" <<'PY'
import os
import sys
import time

deadline = time.time() + 5.0
while time.time() < deadline:
    if os.path.exists(sys.argv[1]):
        sys.exit(0)
    time.sleep(0.005)
sys.exit(1)
PY

python3 - "$TRIGGER_CWD" "$TRIGGER_TMP" <<'PY' &
import os
import sys
import time

deadline = time.time() + 5.0
while time.time() < deadline:
    if any(os.path.exists(path) for path in sys.argv[1:]):
        sys.exit(0)
    time.sleep(0.005)
sys.exit(1)
PY
WATCHER_PID=$!

RC=0
ERR="$(JATTACH_PATH="$WORK_DIR/jattach-tmp" "$JATTACH_BIN" "$TARGET_PID" properties 2>&1 >/dev/null)" || RC=$?
assert_eq "attach without JVM socket exits 1" 1 "$RC"
assert_contains "attach failure diagnostic" "$ERR" "Could not start attach mechanism"

WATCHER_RC=0
wait "$WATCHER_PID" || WATCHER_RC=$?
assert_eq "HotSpot attach trigger file observed" 0 "$WATCHER_RC"

TARGET_RC=0
wait "$TARGET_PID" || TARGET_RC=$?
assert_eq "target received SIGQUIT (handler exit 7)" 7 "$TARGET_RC"
assert_absent "trigger file cleaned up (cwd)" "$TRIGGER_CWD"
assert_absent "trigger file cleaned up (JATTACH_PATH)" "$TRIGGER_TMP"

# ── Artifact sanity ─────────────────────────────────────────────────────────
if python3 - "$JATTACH_BIN" <<'PY'
import struct
import sys

with open(sys.argv[1], "rb") as fh:
    header = fh.read(20)
if header[:4] != b"\x7fELF":
    raise SystemExit("not an ELF file")
if struct.unpack_from("<H", header, 18)[0] != 183:
    raise SystemExit("not AArch64")
PY
then
    pass "packaged artifact is an AArch64 ELF"
else
    fail "packaged artifact is an AArch64 ELF"
fi

echo "[step] jattach consumer tests: $PASS_COUNT passed, $FAIL_COUNT failed"
if [ "$FAIL_COUNT" -ne 0 ]; then
    echo "[fail] $FAIL_COUNT assertion(s) failed"
    exit 1
fi
echo "[ok] all $PASS_COUNT assertions passed"
