#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer functional test for the sockperf executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# Real end-to-end behavior (R34): sockperf server on TCP loopback +
# sockperf ping-pong latency run against 127.0.0.1, asserting the summary.
# /tmp is read-only on OHOS — use $HOME/tmp scratch.
set -euo pipefail

SCRATCH="${TMPDIR:-$HOME/tmp}/sockperf-test-$$"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT
cd "$SCRATCH"

PORT=$((21000 + $$ % 20000))

echo "[test] start sockperf server on 127.0.0.1:$PORT"
sockperf server -p "$PORT" > server.log 2>&1 &
SPID=$!
sleep 2
kill -0 "$SPID" || {
    echo "FAIL: server not running"
    cat server.log
    exit 1
}
echo "OK: server up (pid $SPID)"

echo "[test] run sockperf ping-pong for 2s"
set +e
sockperf ping-pong -i 127.0.0.1 -p "$PORT" --time 2 > client.log 2>&1
RC=$?
set -e
kill "$SPID" 2>/dev/null || true
wait "$SPID" 2>/dev/null || true

[ "$RC" -eq 0 ] || {
    echo "FAIL: sockperf ping-pong exited $RC"
    cat client.log server.log
    exit 1
}
echo "OK: client exited 0"

grep -q "Summary" client.log || {
    echo "FAIL: no summary in client output"
    cat client.log
    exit 1
}
echo "OK: latency summary present"

TOTAL=$(grep -oE "Total [0-9]+ observations" client.log | grep -oE "[0-9]+" | head -1)
[ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ] || {
    echo "FAIL: no measured calls in summary"
    cat client.log
    exit 1
}
echo "OK: $TOTAL measured round trips"
echo "ALL CONSUMER TESTS PASSED"
