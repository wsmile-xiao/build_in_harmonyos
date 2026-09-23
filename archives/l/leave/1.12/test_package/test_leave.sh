#!/usr/bin/env bash
# Generic consumer tests for the packaged leave executable.
#
# leave is a "remind me later" tool: given a valid future time it forks and the
# child enters a nagging loop that sleeps until that time, so the only
# deterministic invocations are those that return immediately.  This script
# therefore drives:
#   T1 invalid minutes (9999)  -> usage on stderr, exit 1
#   T2 hours > 23 (2400)       -> usage on stderr, exit 1
#   T3 non-digit input (12x)   -> usage on stderr, exit 1
#   T4 no argument + EOF       -> prompt on stdout, exit 0 (no fork)
#   T5 valid "+6" (6 minutes)  -> parent exits 0 and the forked child
#                                 announces the alarm; the child is then
#                                 explicitly killed so nothing is left running.
#
# Usage: test_leave.sh <path-to-leave> [workdir]
set -u

BIN="${1:?usage: test_leave.sh <path-to-leave> [workdir]}"
WORKDIR="${2:-$(cd "$(dirname "$0")" && pwd)}"
# Never write test artefacts into the (versioned) test_package directory:
# use the writable scratch directory (R10 — OHOS /tmp is read-only).
SCRATCH="${TMPDIR:-$HOME/tmp}"
mkdir -p "$SCRATCH"
OUT="$SCRATCH/tp-leave-out.txt"
ret=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; shift; for line in "$@"; do echo "    $line"; done; ret=1; }

# T1/T2/T3: invalid time argument -> "Usage: leave [[+]hhmm]" on stderr, exit 1.
check_usage() {
    name="$1"
    arg="$2"
    err="$("$BIN" "$arg" 2>&1 >/dev/null)"
    rc=$?
    if [ "$rc" -eq 1 ] && printf '%s' "$err" | grep -q "Usage: leave"; then
        pass "$name"
    else
        fail "$name" "rc=$rc" "stderr=$err"
    fi
}

check_usage "invalid minutes 9999 -> usage + exit 1" 9999
check_usage "hours 2400 (>23) -> usage + exit 1" 2400
check_usage "non-digit 12x -> usage + exit 1" 12x

# T4: no argument and stdin at EOF -> prompt printed, exit 0, no fork.
out="$(printf '' | "$BIN" 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "When do you have to leave?"; then
    pass "no argument + EOF -> prompt + exit 0"
else
    fail "no argument + EOF" "rc=$rc" "stdout=$out"
fi

# T5: valid "+6" — the parent process returns immediately with status 0 while
# the forked child announces the scheduled alarm.  Poll for that announcement,
# then kill the child (its pid is printed in the message).
: > "$OUT"
"$BIN" +6 > "$OUT" 2>&1
rc=$?
i=0
while [ "$i" -lt 10 ] && ! grep -q "Alarm set for" "$OUT"; do
    sleep 1
    i=$((i + 1))
done

if [ "$rc" -eq 0 ] && grep -q "Alarm set for" "$OUT"; then
    line="$(grep -F 'pid ' "$OUT" | head -n 1)"
    pid="${line##*pid }"
    pid="${pid%%)*}"
    pid="$(printf '%s' "$pid" | tr -dc '0-9')"
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null
        pass "valid +6 -> alarm announced, parent exit 0, child killed"
    else
        fail "valid +6" "no pid found in: $line"
    fi
else
    fail "valid +6" "rc=$rc" "output=$(cat "$OUT" 2>/dev/null)"
fi

echo "---- test_leave.sh: $([ "$ret" -eq 0 ] && echo 'ALL PASS' || echo 'FAILED') ----"
exit "$ret"
