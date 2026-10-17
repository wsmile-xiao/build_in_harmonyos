#!/bin/bash
# test_blockdomains.sh - Smoke test for the blockdomains 0.1 OHOS port.
# Verifies the packaged tools and the daemon's startup path:
#   ACL loading -> "opens library handle" -> NFQUEUE stage.
# The daemon has no --help/--version; on a device without kernel NFQUEUE
# support it exits 1 at nfq_open(), which is the expected clean failure.
# Run by test_package/conanfile.py test() method.
# Usage: test_blockdomains.sh <dir_with_blockdomains_and_blockdomainsctl>

set -euo pipefail

BIN_DIR="${1:-}"
BLOCKDOMAINS_BIN="${BIN_DIR:-}/blockdomains"
CTL_BIN="${BIN_DIR:-}/blockdomainsctl"

fail() { echo "FAIL: $1"; exit 1; }

# Case 1: binaries present and executable
[ -x "$BLOCKDOMAINS_BIN" ] || fail "blockdomains binary missing or not executable: $BLOCKDOMAINS_BIN"
echo "PASS: blockdomains binary present and executable"
[ -f "$CTL_BIN" ] || fail "blockdomainsctl script missing: $CTL_BIN"
echo "PASS: blockdomainsctl script present"

# Case 2: control script prints its usage hint (no root, no side effects)
CTL_OUT=$(sh "$CTL_BIN" badarg 2>&1 || true)
echo "$CTL_OUT" | grep -q "Use start, stop or reload" \
    || fail "blockdomainsctl usage output unexpected: $CTL_OUT"
echo "PASS: blockdomainsctl prints usage hint"

# Case 3: daemon loads a real ACL file and reaches the NFQUEUE stage
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
printf '.example.com\n' > "$WORK/test.acl"

"$BLOCKDOMAINS_BIN" "$WORK/test.acl" > "$WORK/out.log" 2>&1 &
PID=$!
sleep 2

# kill -0 also succeeds on zombies (an exited child not yet wait()ed), so a
# plain kill -0 check would false-pass any startup crash when this script
# runs under a shell that keeps exited background jobs unreaped (bash).
# Classify the process state via /proc first; fall back to ps -o stat=
# when /proc is unavailable.
DAEMON_STATE=""
if [ -r "/proc/$PID/stat" ]; then
    STATE_LINE=$(cat "/proc/$PID/stat" 2>/dev/null || true)
    DAEMON_STATE=${STATE_LINE#*) }      # skip leading "pid (comm) "
    DAEMON_STATE=${DAEMON_STATE%% *}    # first field = process state char
elif command -v ps >/dev/null 2>&1; then
    DAEMON_STATE=$(ps -o stat= -p "$PID" 2>/dev/null | awk '{print $1}' || true)
fi
IS_ZOMBIE=0
case "$DAEMON_STATE" in
Z*) IS_ZOMBIE=1 ;;
esac

if [ "$IS_ZOMBIE" -eq 0 ] && kill -0 "$PID" 2>/dev/null; then
    # The daemon kept running: NFQUEUE opened and it is processing packets.
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
    echo "PASS: blockdomains daemon started and is running (kernel NFQUEUE available)"
    exit 0
fi

RC=0
wait "$PID" 2>/dev/null || RC=$?

grep -q "loads block list" "$WORK/out.log" \
    || fail "daemon did not load the ACL file: $(cat "$WORK/out.log")"
echo "PASS: daemon loaded the ACL file"

grep -q "opens library handle" "$WORK/out.log" \
    || fail "daemon did not reach the NFQUEUE stage: $(cat "$WORK/out.log")"
echo "PASS: daemon reached the NFQUEUE (nfq_open) stage"

if [ "$RC" -eq 1 ] && grep -q "nfq_open" "$WORK/out.log"; then
    echo "PASS: daemon exited cleanly at nfq_open (kernel NFQUEUE unavailable on device)"
    exit 0
fi

fail "unexpected daemon exit (rc=$RC): $(cat "$WORK/out.log")"
