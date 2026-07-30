#!/usr/bin/env sh
# test_pidof.sh — test_package for pidof 2.86 (R34)
#
# pidof is a CLI tool that reads /proc to find PIDs of running programs.
# This test drives the real binary against /proc (not a stub): it verifies
# pidof can find a process by name and that it reports a missing one.
#
# The binary path is passed as $1 by test_package/conanfile.py.
set -u

PIDOF_BIN="$1"
FAILURES=0

check() {
    if eval "$1"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "Testing pidof binary: $PIDOF_BIN"

# Case 1: pidof finds itself. Running "$PIDOF_BIN pidof" makes pidof scan
# /proc and locate its own process (comm == basename "pidof"), proving the
# /proc-reading core works end-to-end.
check '"$PIDOF_BIN" pidof > /dev/null 2>&1' \
    "pidof can find the running pidof process"

# Case 2: pidof on a nonexistent program must return empty output and a
# non-zero exit code.
OUTPUT=$("$PIDOF_BIN" __nonexistent_program_xyzzy__ 2>/dev/null) && RC=0 || RC=$?
check '[ "$RC" -ne 0 ] && [ -z "$OUTPUT" ]' \
    "pidof nonexistent program: exit != 0 and no output"

if [ "$FAILURES" -eq 0 ]; then
    echo "All tests passed"
    exit 0
else
    echo "$FAILURES test(s) failed"
    exit 1
fi
