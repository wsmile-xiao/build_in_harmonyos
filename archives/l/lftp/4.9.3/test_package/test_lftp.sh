#!/bin/sh
# test_lftp.sh -- offline functional tests for the packaged lftp binary.
# Called by test_package/conanfile.py test() method via bash.
#
# Four checks, all offline (no network): version string, help output,
# queued kill/jobs behaviour (ported from upstream tests/lftp-queue-kill),
# and local lcd/lpwd. Counters are owned by this script; the final line
# prints HMBS_TEST_PACKAGE_RESULT for the rule4 gate (no stdout scraping).
#
# NOTE on `set`: `set -u` plus `pipefail` are on, but `set -e` is
# deliberately OFF -- this is a counting harness: an early exit on the
# first failing check would suppress the HMBS marker line and hide the
# passedCount/discovered figures the gate requires.

set -u
set -o pipefail 2>/dev/null || true

TOTAL=4
PASSED=0

# Work dir honours the task TMPDIR injected by hmbs, else /tmp.
BASE_TMP="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$BASE_TMP/lftp_test_XXXXXX")" || exit 1
cleanup() {
    rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# --- check 1: version string carries name + version (content, not just rc)
if lftp --version > "$WORK/version.txt" 2>&1 \
    && grep -q "lftp" "$WORK/version.txt" \
    && grep -q "4\.9\.3" "$WORK/version.txt"; then
    echo "PASS t1 version string"
    PASSED=$((PASSED + 1))
else
    echo "FAIL t1 version string"
    cat "$WORK/version.txt" 2>/dev/null || true
fi

# --- check 2: help command runs and lists real commands (non-empty, offline)
if lftp -c 'help' > "$WORK/help.txt" 2>&1 \
    && test -s "$WORK/help.txt" \
    && grep -qi "open" "$WORK/help.txt"; then
    echo "PASS t2 help output"
    PASSED=$((PASSED + 1))
else
    echo "FAIL t2 help output"
    cat "$WORK/help.txt" 2>/dev/null || true
fi

# --- check 3: queue/kill/jobs offline behaviour (upstream lftp-queue-kill)
# "kill all" must terminate queued commands too, leaving jobs output empty.
JOBS_OUT="$(lftp <<EOF 2>/dev/null
queue sleep 30
queue sleep 31
kill all
jobs
EOF
)"
JOBS_RC=$?
# Both conditions: session exited cleanly AND jobs output is empty
# (rc check prevents a false pass when lftp itself fails to run).
if test "$JOBS_RC" -eq 0 && test -z "$JOBS_OUT"; then
    echo "PASS t3 queue kill jobs"
    PASSED=$((PASSED + 1))
else
    echo "FAIL t3 queue kill jobs (jobs output not empty)"
    printf '%s\n' "$JOBS_OUT"
fi

# --- check 4: local lcd/lpwd roundtrip inside the temp dir
if lftp -c "lcd \"$WORK\"; lpwd" > "$WORK/lpwd.txt" 2>&1 \
    && grep -qx "$WORK" "$WORK/lpwd.txt"; then
    echo "PASS t4 lcd lpwd"
    PASSED=$((PASSED + 1))
else
    echo "FAIL t4 lcd lpwd"
    cat "$WORK/lpwd.txt" 2>/dev/null || true
fi

echo "Results: $PASSED/$TOTAL consumer checks passed"
if test "$PASSED" -eq "$TOTAL"; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test_lftp.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test_lftp.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
    exit 1
fi
