#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer loopback test for the packaged uperf.
# Runs in conanrun env (PATH includes the installed bin/).
# Starts a slave on localhost:20000, runs a master plan, asserts:
#   1) master exits 0
#   2) master prints "Run Statistics"
#   3) statistics report the 128 bytes written by the plan
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

UPERF="$(command -v uperf)" || { echo "[test] uperf not found in PATH" >&2; exit 1; }
echo "[test] using uperf: $UPERF"

"$UPERF" -s > "$WORK/slave.log" 2>&1 &
SPID=$!
sleep 2

h=localhost duration=5s "$UPERF" -m "$DIR/consumer_tcp.xml" > "$WORK/master.log" 2>&1
RC=$?
kill -9 "$SPID" 2>/dev/null

if [ "$RC" -ne 0 ]; then
    echo "[test] FAIL: master exited $RC" >&2
    tail -20 "$WORK/master.log" >&2
    exit 1
fi
echo "[test] assertion 1 OK: master exit 0"

grep -q "Run Statistics" "$WORK/master.log" || {
    echo "[test] FAIL: no Run Statistics in master output" >&2
    tail -20 "$WORK/master.log" >&2
    exit 1
}
echo "[test] assertion 2 OK: Run Statistics present"

grep -q "128.00B" "$WORK/master.log" || {
    echo "[test] FAIL: expected 128.00B transferred not found" >&2
    cat "$WORK/master.log" >&2
    exit 1
}
echo "[test] assertion 3 OK: 128.00B transferred"

echo "[test] consumer OK: packaged uperf loopback transaction"
exit 0
