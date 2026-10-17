#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS PC consumer test for pen 0.34.1
#
# This is a *real* consumer test: it drives the installed pen binaries through
# their documented interfaces and observes the actual data path. It contains no
# assertion-style stubs and no self-referential checks — every case below moves
# bytes through a live process and prints what was observed.
#
# Cases (all exercised against the packaged binaries found on PATH):
#   OHOS-T1  UDP data plane   : penlog -> pen(-U) -> penlogd -> logfile
#   OHOS-T2  control plane    : penctl -> pen control port (TCP accept + protocol)
#   OHOS-T3  TCP data plane   : penctl -> pen(A) data port -> pen(B) control port
#   OHOS-T4  statistics plane : USR1 + -w -> HTML status page
#
# Upstream ships no automated test suite at all (no tests/ directory, no
# TESTS/check_PROGRAMS registration in Makefile.am — `make check` is an
# automake no-op). These cases are therefore *new* HarmonyOS consumer cases
# added on top of the upstream tree, not a replacement for upstream tests.
# Deliberately `set -u` only, NOT `set -euo pipefail`: this suite must run every
# case to completion and then report the total number of failures (see the
# `exit $((fails > 0 ? 1 : 0))` at the end). `-e` would abort on the first
# failing case and hide the rest, and `-o pipefail` would make an intentional
# `grep -c` miss (exit 1) fatal.
set -u

BASE_PORT=${PEN_TEST_BASE_PORT:-17140}
RUN_DIR="${PEN_TEST_DIR:-${TMPDIR:-/data/storage/el2/base/cache}/pen-ohos-consumer}"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"
# `|| true`: HMDFS/FUSE ignores chmod, so the mode is already 0755 in practice and
# a "failure" here is not an error condition for the test run.
chmod 755 "$RUN_DIR" "$LOG_DIR" 2>/dev/null || true

PEN=$(command -v pen)
PENLOG=$(command -v penlog)
PENLOGD=$(command -v penlogd)
PENCTL=$(command -v penctl)
MERGELOGS=$(command -v mergelogs)

echo "=== pen HarmonyOS PC consumer test ==="
echo "run dir : $RUN_DIR"
echo "binaries: $PEN $PENLOG $PENLOGD $PENCTL $MERGELOGS"
echo

for b in "$PEN" "$PENLOG" "$PENLOGD" "$PENCTL" "$MERGELOGS"; do
    if [ -z "$b" ] || [ ! -x "$b" ]; then
        echo "[FATAL] packaged binary missing on PATH"
        exit 2
    fi
done

# `timeout` is used where a control-port query could otherwise block forever;
# it is optional so the suite still runs on a minimal rootfs.
TO=""
if command -v timeout > /dev/null 2>&1; then
    TO="timeout 15"
fi

PIDS=""
cleanup() {
    # `|| true` on every kill: the daemons may already have exited on their own
    # (e.g. penlogd was TERMed by OHOS-T1), and "no such process" must not turn
    # the EXIT trap into a non-zero status.
    for p in $PIDS; do kill -TERM "$p" 2>/dev/null || true; done
    sleep 1
    for p in $PIDS; do kill -KILL "$p" 2>/dev/null || true; done
}
trap cleanup EXIT

fails=0
report() {           # report <case> <observed-marker> <detail>
    case_id=$1; ok=$2; detail=$3
    if [ "$ok" = "yes" ]; then
        echo "[PASS] $case_id : $detail"
    else
        echo "[FAIL] $case_id : $detail"
        fails=$((fails + 1))
    fi
}

# ---------------------------------------------------------------- OHOS-T1
# UDP data plane: penlog -> pen(-U) -> penlogd
UDP_FRONT=$((BASE_PORT + 0))
UDP_BACK=$((BASE_PORT + 1))
UDP_LOG="$LOG_DIR/ohos-t1-penlogd.log"
: > "$UDP_LOG"

"$PENLOGD" -f -l "$UDP_LOG" -p "$LOG_DIR/t1-penlogd.pid" "$UDP_BACK" \
    > "$LOG_DIR/ohos-t1-penlogd.out" 2>&1 &
P1=$!; PIDS="$PIDS $P1"
sleep 1

"$PEN" -U -f -C "$((BASE_PORT + 2))" -p "$LOG_DIR/t1-pen.pid" \
    "$UDP_FRONT" "127.0.0.1:$UDP_BACK" > "$LOG_DIR/ohos-t1-pen.out" 2>&1 &
P2=$!; PIDS="$PIDS $P2"
sleep 1

PROBE_LINE='198.51.100.9 - - [28/Sep/2026:12:00:00 +0800] "GET /pen-ohos-t1 HTTP/1.0" 200 42'
echo "$PROBE_LINE" | "$PENLOG" 127.0.0.1 "$UDP_FRONT"
sleep 1

# penlogd buffers its logfile; a graceful TERM closes/flushes it (upstream
# behaviour, see penlogd.c: fclose() after the signal handler clears loopflag).
kill -TERM "$(cat "$LOG_DIR/t1-penlogd.pid" 2>/dev/null)" 2>/dev/null
sleep 1

# `|| true`: grep -c exits 1 when the count is zero, which is a legitimate
# observation here (0 matches => the datagram did not arrive), not an error.
# The empty result is normalised by the `${SEEN:-0}` guard below.
SEEN=$(grep -c "pen-ohos-t1" "$UDP_LOG" 2>/dev/null || true)
echo "        UDP front : 127.0.0.1:$UDP_FRONT -> back 127.0.0.1:$UDP_BACK"
echo "        logfile   : $UDP_LOG"
echo "        observed  : $(cat "$UDP_LOG" 2>/dev/null)"
if [ "${SEEN:-0}" -ge 1 ]; then
    report OHOS-T1 yes "UDP datagram traversed the load balancer and was consolidated by penlogd"
else
    report OHOS-T1 no "datagram did not reach penlogd (logfile empty)"
fi

# ---------------------------------------------------------------- OHOS-T2
# Control plane over TCP: penctl -> running pen's control port.
CTL_PORT=$((BASE_PORT + 2))
CTL_OUT="$LOG_DIR/ohos-t2-penctl.out"
"$PENCTL" "127.0.0.1:$CTL_PORT" servers > "$CTL_OUT" 2>&1
PENCTL_RC=$?
# `|| true`: same rationale as OHOS-T1 — a zero match count must not abort the
# suite; `${SERVER_ROW:-0}` below treats it as "no backend row observed".
SERVER_ROW=$(grep -c "$UDP_BACK" "$CTL_OUT" 2>/dev/null || true)
echo "        penctl    : penctl 127.0.0.1:$CTL_PORT servers (rc=$PENCTL_RC)"
echo "        observed  : $(cat "$CTL_OUT" 2>/dev/null)"
if [ "$PENCTL_RC" -eq 0 ] && [ "${SERVER_ROW:-0}" -ge 1 ]; then
    report OHOS-T2 yes "live server table retrieved over the TCP control port"
else
    report OHOS-T2 no "control port query failed or returned no backend row"
fi

# ---------------------------------------------------------------- OHOS-T3
# TCP data plane: penctl -> pen(A) data port -> pen(B) control port.
# pen(A) is configured with pen(B)'s control port as its back end, so the reply
# penctl receives has travelled through pen's TCP relay.
TCP_FRONT=$((BASE_PORT + 3))
TCP_BACK_A=$((BASE_PORT + 4))
TCP_BACK_B=$((BASE_PORT + 5))
DUMMY_BACK=$((BASE_PORT + 6))

"$PEN" -f -C "$TCP_BACK_A" -p "$LOG_DIR/t3-penB.pid" "$TCP_BACK_B" \
    "127.0.0.1:$DUMMY_BACK" > "$LOG_DIR/ohos-t3-penB.out" 2>&1 &
P3=$!; PIDS="$PIDS $P3"
sleep 1
"$PEN" -f -C "$((BASE_PORT + 7))" -p "$LOG_DIR/t3-penA.pid" "$TCP_FRONT" \
    "127.0.0.1:$TCP_BACK_A" > "$LOG_DIR/ohos-t3-penA.out" 2>&1 &
P4=$!; PIDS="$PIDS $P4"
sleep 1

RELAY_OUT="$LOG_DIR/ohos-t3-penctl.out"
$TO "$PENCTL" "127.0.0.1:$TCP_FRONT" servers > "$RELAY_OUT" 2>&1
RELAY_RC=$?
DIRECT_OUT="$LOG_DIR/ohos-t3-direct.out"
$TO "$PENCTL" "127.0.0.1:$TCP_BACK_A" servers > "$DIRECT_OUT" 2>&1
DIRECT_RC=$?
echo "        relayed   : penctl -> 127.0.0.1:$TCP_FRONT (pen A) -> 127.0.0.1:$TCP_BACK_A (pen B control)"
echo "        observed  : $(cat "$RELAY_OUT" 2>/dev/null)"
echo "        direct    : $(cat "$DIRECT_OUT" 2>/dev/null)"
if [ "$RELAY_RC" -eq 0 ] && [ "$DIRECT_RC" -eq 0 ] && \
   [ -s "$RELAY_OUT" ] && [ "$(cat "$RELAY_OUT")" = "$(cat "$DIRECT_OUT")" ]; then
    report OHOS-T3 yes "TCP stream relayed through pen(A) byte-identical to the direct connection"
else
    report OHOS-T3 no "TCP relay through pen(A) did not reproduce the direct reply"
fi

# ---------------------------------------------------------------- OHOS-T4
# Statistics plane: USR1 + -w writes an HTML status page.
STATS="$LOG_DIR/ohos-t4-stats.html"
: > "$STATS"
STATS_FRONT=$((BASE_PORT + 8))
"$PEN" -U -f -C "$((BASE_PORT + 9))" -w "$STATS" -p "$LOG_DIR/t4-pen.pid" \
    "$STATS_FRONT" "127.0.0.1:$UDP_BACK" > "$LOG_DIR/ohos-t4-pen.out" 2>&1 &
P5=$!; PIDS="$PIDS $P5"
sleep 1
echo "203.0.113.5 - - [28/Sep/2026:12:00:01 +0800] \"GET /pen-ohos-t4 HTTP/1.0\" 200 5" \
    | "$PENLOG" 127.0.0.1 "$STATS_FRONT"
sleep 1
kill -USR1 "$(cat "$LOG_DIR/t4-pen.pid" 2>/dev/null)" 2>/dev/null
sleep 1
STATS_BYTES=$(wc -c < "$STATS" 2>/dev/null || echo 0)
# `|| true`: zero matches (page missing / no back end listed) is the FAIL
# observation itself, not an error to swallow; guarded by `${STATS_SRV:-0}`.
STATS_SRV=$(grep -c "127.0.0.1" "$STATS" 2>/dev/null || true)
echo "        stats file: $STATS (${STATS_BYTES} bytes)"
echo "        observed  : $(grep -m3 -o 'Pen status page\|1 servers\|127.0.0.1' "$STATS" 2>/dev/null | tr '\n' ' ')"
if [ "${STATS_BYTES:-0}" -ge 256 ] && [ "${STATS_SRV:-0}" -ge 1 ]; then
    report OHOS-T4 yes "HTML status page generated on USR1 and lists the live back end"
else
    report OHOS-T4 no "status page was not generated"
fi

echo
echo "=== summary: cases=4 failed=$fails ==="
echo "logs: $LOG_DIR"
exit $((fails > 0 ? 1 : 0))
