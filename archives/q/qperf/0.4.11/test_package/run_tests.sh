#!/bin/sh
# Consumer test for the packaged qperf executable.
#
# Every assertion drives the installed binary: version reporting, transport
# inventory, ELF dependency coherence, real client/server loopback measurements
# over TCP and UDP, an explicit attempt at every remaining transport the binary
# registers (SCTP, SDP, RDS), and a teardown through upstream's own "quit"
# test.  Nothing here is a placeholder: each check inspects program output, and
# a check that cannot be evaluated fails rather than being skipped silently.
#
# Field names match qperf's real output, measured on HarmonyOS:
#   tcp_bw   -> "    bw  =  4.23 GB/sec"
#   tcp_lat  -> "    latency  =  31.6 us"
#   udp_bw   -> "    send_bw  =  3.54 GB/sec" / "    recv_bw  =  1.69 GB/sec"
#   udp_lat  -> "    latency  =  28.9 us"
#
# The SCTP/SDP/RDS block below is an *attempt*, but an adjudicable one
# (tightened in the z32c round).  The previous rule was
# "(rc==0 && measured>0) || (rc!=0 && diagnosed>0)", which scored ok on both
# branches and therefore said nothing about transport capability: the
# "diagnostic" it matched on was the client's "getaddrinfo failed: Unrecognized
# service", which notes.md proves to be a downstream artifact (the server child
# dies before sending its data port, so the client uses 0xFFFFFFFF as the
# service string).  The real refusal sentences were only ever printed by the
# server, and the shared server log was never read by the assertion.
#
# New rule, one assertion per transport:
#   * the transport gets its own server, its own listen port and its own log
#     file, so the answer on the wire is unambiguously attributable to it;
#   * ok requires either a real measurement (rc==0 plus a measured field) or
#     the genuine kernel socket-layer refusal for that transport
#     ("unable to make SCTP socket", "unable to make SDP socket", or
#      "socket failed: Address family not supported", server or client side);
#   * anything else is a failure, so a silent hang, a silent zero or an
#     unattributable message can no longer be counted as a verdict.
set -u

QP="${1:-qperf}"
WORK="${2:-.}"
PORT="${QPERF_TEST_PORT:-19821}"
SERVER_LOG="$WORK/qperf-server.log"
PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
no() { FAIL=$((FAIL + 1)); printf '  [FAIL] %s\n' "$1"; }

if [ ! -f "$QP" ]; then
    printf 'packaged qperf not found at %s\n' "$QP" >&2
    printf 'RESULT pass=0 fail=1 total=1\n'
    exit 1
fi

# ---------------------------------------------------------------- 1. version
VER_OUT="$("$QP" --version 2>&1)"
RC=$?
if [ "$RC" -eq 0 ]; then ok "--version exits 0"; else no "--version exits 0 (rc=$RC)"; fi
if [ "$VER_OUT" = "qperf 0.4.11" ]; then
    ok "--version reports the packaged upstream version"
else
    no "--version reports 'qperf 0.4.11' (got: $VER_OUT)"
fi

# ------------------------------------------------------- 2. transport inventory
HELP="$("$QP" --help tests 2>&1)"
RC=$?
if [ "$RC" -eq 0 ]; then
    ok "--help tests exits 0"
else
    no "--help tests exits 0 (rc=$RC)"
fi
for t in tcp_bw tcp_lat udp_bw udp_lat; do
    if printf '%s\n' "$HELP" | grep -q "$t"; then
        ok "transport inventory advertises $t"
    else
        no "transport inventory advertises $t"
    fi
done

if printf '%s\n' "$HELP" | grep -q 'rc_bw'; then HAVE_RDMA_TESTS=1; else HAVE_RDMA_TESTS=0; fi
printf '  [INFO] RDMA (rc_*) tests advertised: %s\n' "$HAVE_RDMA_TESTS"

# ------------------------------------------------- 3. link / inventory coherence
# A non-RDMA build must not carry libibverbs among its DT_NEEDED entries and an
# RDMA build must.  This asserts the two views agree instead of trusting either.
# readelf is used rather than ldd because HarmonyOS ships no ldd; a missing
# reader is reported as a failure so the count can never be padded by a skip.
READER=""
for c in readelf llvm-readelf greadelf; do
    p=$(command -v "$c" 2>/dev/null)
    if [ -n "$p" ]; then READER="$p"; break; fi
done
[ -n "$READER" ] || READER=/data/service/hnp/bin/llvm-readelf
if [ -f "$READER" ]; then
    DEPS=$("$READER" -d "$QP" 2>/dev/null)
    if printf '%s\n' "$DEPS" | grep -q 'libibverbs'; then
        LINKS_IBVERBS=1
    else
        LINKS_IBVERBS=0
    fi
    if [ "$LINKS_IBVERBS" = "$HAVE_RDMA_TESTS" ]; then
        ok "dynamic dependencies agree with advertised transports (libibverbs=$LINKS_IBVERBS, rc_tests=$HAVE_RDMA_TESTS)"
    else
        no "dynamic dependencies disagree with transports (libibverbs=$LINKS_IBVERBS vs rc_bw=$HAVE_RDMA_TESTS)"
    fi
    printf '  [INFO] %s -d NEEDED entries:\n' "$READER"
    printf '%s\n' "$DEPS" | grep -i 'NEEDED' | sed 's/^/      /'
else
    no "ELF reader unavailable ($READER), link coherence could not be evaluated"
fi

# ---------------------------------------------------------- 4. loopback server
"$QP" -lp "$PORT" >"$SERVER_LOG" 2>&1 &
SRV=$!
i=0
while [ "$i" -lt 30 ] && kill -0 "$SRV" 2>/dev/null; do
    if "$QP" 127.0.0.1 -lp "$PORT" conf -t 1 >/dev/null 2>&1; then break; fi
    i=$((i + 1))
    sleep 0.2
done
if kill -0 "$SRV" 2>/dev/null; then
    ok "server mode starts and stays resident on port $PORT"
else
    no "server mode starts on port $PORT"
    sed 's/^/      /' "$SERVER_LOG"
fi

# The qperf server child handling a refused transport exits, so make sure the
# master is still there before every block that needs it.  This only ever
# reaps/starts the server this script itself launched, by its own PID.
ensure_server() {
    if kill -0 "$SRV" 2>/dev/null; then return 0; fi
    printf '  [INFO] server pid %s is gone, restarting it on port %s\n' "$SRV" "$PORT"
    "$QP" -lp "$PORT" >>"$SERVER_LOG" 2>&1 &
    SRV=$!
    j=0
    while [ "$j" -lt 30 ]; do
        if "$QP" 127.0.0.1 -lp "$PORT" conf -t 1 >/dev/null 2>&1; then break; fi
        j=$((j + 1))
        sleep 0.2
    done
    kill -0 "$SRV" 2>/dev/null
}

# check_field <log> <test-name> <field>  -- one assertion for presence and one
# for a strictly positive numeric value.
check_field() {
    log="$1"; name="$2"; field="$3"
    line=$(grep -E "^[[:space:]]*${field}[[:space:]]*=" "$log" 2>/dev/null | head -1)
    if [ -z "$line" ]; then
        no "loopback $name reports a '$field' measurement"
        return
    fi
    ok "loopback $name reports a '$field' measurement"
    val=$(printf '%s\n' "$line" | sed -E 's/.*=[[:space:]]*//; s/[[:space:]]*$//')
    num=$(printf '%s\n' "$val" | sed -E 's/[^0-9.].*$//')
    if [ -z "$num" ]; then
        no "loopback $name $field is numeric (got '$val')"
        return
    fi
    pos=$(awk -v v="$num" 'BEGIN { print (v + 0 > 0) ? "yes" : "no" }')
    if [ "$pos" = "yes" ]; then
        ok "loopback $name $field is non-zero ($val)"
    else
        no "loopback $name $field is non-zero (got '$val')"
    fi
}

# run_cmd <seconds> <logfile> <args...> -- wrap in timeout when it is available.
# timeout is resolved by executability, not by command -v: on HarmonyOS toybox
# sh, command -v timeout prints the shell alias text instead of a path.
run_cmd() {
    secs="$1"; log="$2"
    shift 2
    if [ -x /usr/bin/timeout ]; then
        /usr/bin/timeout "$secs" "$@" >"$log" 2>&1
    elif [ -x "$HOME/usr/local/bin/timeout" ]; then
        "$HOME/usr/local/bin/timeout" "$secs" "$@" >"$log" 2>&1
    else
        "$@" >"$log" 2>&1
    fi
}

run_measure() {
    name="$1"
    shift
    log="$WORK/$name.client.log"
    ensure_server || { no "loopback $name has a live server to talk to"; return; }
    run_cmd 90 "$log" "$QP" 127.0.0.1 -lp "$PORT" -t 1 "$name"
    rc=$?
    printf '  [INFO] qperf 127.0.0.1 -lp %s -t 1 %s -> rc=%s\n' "$PORT" "$name" "$rc"
    sed 's/^/      /' "$log"
    if [ "$rc" -ne 0 ]; then
        no "loopback $name completes (rc=$rc)"
        return
    fi
    ok "loopback $name completes (rc=0)"
    for f in "$@"; do
        check_field "$log" "$name" "$f"
    done
}

run_measure tcp_bw  bw
run_measure tcp_lat latency
run_measure udp_lat latency
run_measure udp_bw  send_bw recv_bw

# ------------------------------------- 5. remaining registered transports: attempt
# SCTP, SDP and RDS are registered by this build (see --help tests above) but the
# HongMeng kernel may not implement their protocol families.  Each transport is
# driven against *its own* server (own listen port, own log file, reaped by its
# own PID) and the single assertion for it passes only on a real measurement or
# on that transport's genuine kernel-level refusal, read from the server log as
# well as the client log.  The errno-level root cause is in notes.md.
ATTEMPT_SEQ=0
attempt_transport() {
    name="$1"
    refusal="$2"
    ATTEMPT_SEQ=$((ATTEMPT_SEQ + 1))
    aprt=$((PORT + 20 + ATTEMPT_SEQ))
    slog="$WORK/$name.server.log"
    log="$WORK/$name.attempt.log"
    : >"$slog"
    : >"$log"
    "$QP" -lp "$aprt" >>"$slog" 2>&1 &
    asrv=$!
    k=0
    while [ "$k" -lt 30 ]; do
        if "$QP" 127.0.0.1 -lp "$aprt" conf -t 1 >/dev/null 2>&1; then break; fi
        k=$((k + 1))
        sleep 0.2
    done
    if ! kill -0 "$asrv" 2>/dev/null; then
        no "attempt $name: dedicated server never came up on port $aprt"
        return
    fi
    run_cmd 90 "$log" "$QP" 127.0.0.1 -lp "$aprt" -t 1 "$name"
    rc=$?
    measured=$(grep -cE '^[[:space:]]*(bw|latency|send_bw|recv_bw)[[:space:]]*=' "$log" 2>/dev/null)
    refused_server=$(grep -c "$refusal" "$slog" 2>/dev/null)
    refused_client=$(grep -c "$refusal" "$log" 2>/dev/null)
    kill "$asrv" 2>/dev/null
    k=0
    while [ "$k" -lt 25 ] && kill -0 "$asrv" 2>/dev/null; do
        k=$((k + 1))
        sleep 0.2
    done
    kill -9 "$asrv" 2>/dev/null
    printf '  [INFO] attempt %s on dedicated port %s -> rc=%s measured_lines=%s server_refusal_lines=%s client_refusal_lines=%s pattern=[%s]\n' \
        "$name" "$aprt" "$rc" "$measured" "$refused_server" "$refused_client" "$refusal"
    sed 's/^/      [client] /' "$log"
    sed 's/^/      [server] /' "$slog"
    if [ "$rc" -eq 0 ] && [ "$measured" -gt 0 ]; then
        ok "attempt $name: transport implemented here, measurement reported"
    elif [ "$refused_server" -gt 0 ] || [ "$refused_client" -gt 0 ]; then
        ok "attempt $name: refused at the kernel socket layer ('$refusal'), no hang (rc=$rc)"
    else
        no "attempt $name: neither measured nor refused at the socket layer (rc=$rc), the result is not adjudicable"
    fi
}

# The refusal strings below are upstream's own output, taken from the pristine
# tree: socket.c:636/678 "unable to make %s socket" (kind_name = SCTP / SDP) and
# rds.c:342/414/479 error(SYS, "socket failed") -> "socket failed: Address family
# not supported by protocol".
attempt_transport sctp_bw "unable to make SCTP socket"
attempt_transport sctp_lat "unable to make SCTP socket"
attempt_transport sdp_bw "unable to make SDP socket"
attempt_transport sdp_lat "unable to make SDP socket"
attempt_transport rds_bw "socket failed: Address family not supported"
attempt_transport rds_lat "socket failed: Address family not supported"

# ------------------------------------------------------ 6. server teardown
ensure_server || { no "server alive before the quit test"; }
run_cmd 60 "$WORK/quit.client.log" "$QP" 127.0.0.1 -lp "$PORT" quit
if [ $? -eq 0 ]; then
    ok "client 'quit' test is accepted by the server"
else
    no "client 'quit' test is accepted by the server"
fi
i=0
while [ "$i" -lt 30 ] && kill -0 "$SRV" 2>/dev/null; do
    i=$((i + 1))
    sleep 0.2
done
if kill -0 "$SRV" 2>/dev/null; then
    no "server exits after the quit test"
    kill "$SRV" 2>/dev/null
else
    ok "server exits after the quit test"
fi

TOTAL=$((PASS + FAIL))
printf 'RESULT pass=%d fail=%d total=%d\n' "$PASS" "$FAIL" "$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
