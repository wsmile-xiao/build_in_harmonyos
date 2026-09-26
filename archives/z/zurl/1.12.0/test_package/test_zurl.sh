#!/bin/sh
# test_package consumer test — zurl (ZeroMQ HTTP/WebSocket client daemon).
# Runs in conanrun env against the packaged binary (absolute path in $1):
#   1) `zurl --version` prints "Zurl 1.12.0" (binary runs, version correct)
#   2) arm64 ELF + ldd resolves every dependency (static smoke, baka style)
#   3) daemon start/stop with a tcp loopback config: log shows "started",
#      SIGTERM leads to a clean exit ("stopped") — proves the Qt/zmq/curl
#      runtime chain is really usable, not just linked.
# Results are reported with a real-count HMBS_TEST_PACKAGE_RESULT marker;
# any failure exits non-zero.
set -eu

ZURL_BIN="${1:-zurl}"
PASS=0
FAIL=0

report() {
    # $1=name $2=ok(1/0)
    if [ "$2" = "1" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $1"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $1" >&2
    fi
}

# --- case 1: --version ---
if [ -x "$ZURL_BIN" ]; then
    ver_out="$("$ZURL_BIN" --version 2>&1 || true)"
    if [ "$ver_out" = "Zurl 1.12.0" ]; then
        report "zurl --version prints Zurl 1.12.0" 1
    else
        echo "unexpected --version output: $ver_out" >&2
        report "zurl --version prints Zurl 1.12.0" 0
    fi
else
    echo "$ZURL_BIN not found or not executable" >&2
    report "zurl --version prints Zurl 1.12.0" 0
fi

# --- case 2: ELF arch + dependency resolution ---
if file "$ZURL_BIN" 2>/dev/null | grep -qE "ELF.*64-bit.*arm64"; then
    report "zurl is an arm64 ELF binary" 1
else
    echo "not an arm64 ELF binary: $(file "$ZURL_BIN" 2>/dev/null)" >&2
    report "zurl is an arm64 ELF binary" 0
fi

if command -v ldd >/dev/null 2>&1; then
    missing="$(ldd "$ZURL_BIN" 2>&1 | grep -E "not found|Error loading" || true)"
    if [ -z "$missing" ]; then
        report "ldd resolves all dynamic dependencies" 1
    else
        echo "unresolved dynamic dependencies:" >&2
        echo "$missing" >&2
        report "ldd resolves all dynamic dependencies" 0
    fi
else
    # ldd unavailable: count the check as passed only if case 1 already
    # proved the binary executes (dynamic loader resolved it at exec).
    if [ "$PASS" -ge 1 ]; then
        report "ldd resolves all dynamic dependencies (via exec proof)" 1
    else
        report "ldd resolves all dynamic dependencies (via exec proof)" 0
    fi
fi

# --- case 3: daemon start/stop with tcp loopback config ---
# ZMQ ipc (unix socket) path limit (~107 chars) is exceeded by the HMBS
# TMPDIR prefix (/storage/.../runtime/zurl-1.12.0/tmp/zurl-test.XXXXXX/zurl-in
# ~= 108 chars -> "unable to bind to in_spec"). tcp loopback has no path
# limit and exercises the same Qt/zmq/curl runtime chain.
TMP_BASE="${TMPDIR:-${TMP:-/tmp}}"
WORK_DIR="$(mktemp -d "$TMP_BASE/zurl-test.XXXXXX")"
# shellcheck disable=SC2064
trap "rm -rf \"$WORK_DIR\"" EXIT INT TERM
# Allocate 4 distinct free loopback ports in one python call (single call
# keeps the sockets bound while sampling, so ports cannot repeat; fallback
# to PID-derived ports when python3 is unavailable).
if command -v python3 >/dev/null 2>&1; then
    _ports="$(python3 -c 'import socket; ss=[socket.socket() for _ in range(4)]; [s.bind(("127.0.0.1", 0)) for s in ss]; print(" ".join(str(s.getsockname()[1]) for s in ss)); [s.close() for s in ss]')"
    P_IN="$(echo "$_ports" | cut -d ' ' -f 1)"
    P_IN_STREAM="$(echo "$_ports" | cut -d ' ' -f 2)"
    P_OUT="$(echo "$_ports" | cut -d ' ' -f 3)"
    P_REQ="$(echo "$_ports" | cut -d ' ' -f 4)"
else
    _base=$(date +%s 2>/dev/null || echo 20000)
    _base=$((20000 + _base % 20000))
    P_IN="$_base"; P_IN_STREAM="$((_base + 1))"; P_OUT="$((_base + 2))"; P_REQ="$((_base + 3))"
fi
cat > "$WORK_DIR/zurl.conf" <<EOF
[General]
instance_id=
in_spec=tcp://127.0.0.1:$P_IN
in_stream_spec=tcp://127.0.0.1:$P_IN_STREAM
out_spec=tcp://127.0.0.1:$P_OUT
in_req_spec=tcp://127.0.0.1:$P_REQ
defpolicy=allow
allow=
allow_ipv6=false
max_open_requests=10
buffer_size=200000
timeout=30
in_hwm=100
out_hwm=100
EOF
"$ZURL_BIN" --config="$WORK_DIR/zurl.conf" > "$WORK_DIR/zurl.log" 2>&1 &
ZURL_PID=$!
started=0
i=0
while [ "$i" -lt 100 ]; do
    if grep -q "started" "$WORK_DIR/zurl.log" 2>/dev/null; then
        started=1
        break
    fi
    if ! kill -0 "$ZURL_PID" 2>/dev/null; then
        break
    fi
    sleep 0.1
    i=$((i + 1))
done
if [ "$started" = "1" ]; then
    kill -TERM "$ZURL_PID" 2>/dev/null || true
    wait "$ZURL_PID" 2>/dev/null || true
    if grep -q "stopped" "$WORK_DIR/zurl.log" 2>/dev/null; then
        report "daemon starts (started) and stops cleanly (stopped)" 1
    else
        echo "daemon started but no clean stop; log:" >&2
        cat "$WORK_DIR/zurl.log" >&2 || true
        report "daemon starts (started) and stops cleanly (stopped)" 0
    fi
else
    echo "daemon never reached started state; log:" >&2
    cat "$WORK_DIR/zurl.log" >&2 || true
    kill -TERM "$ZURL_PID" 2>/dev/null || true
    wait "$ZURL_PID" 2>/dev/null || true
    report "daemon starts (started) and stops cleanly (stopped)" 0
fi

DISCOVERED=$((PASS + FAIL))
if [ "$FAIL" -ne 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test_zurl.sh <zurl>\",\"discovered\":${DISCOVERED},\"passedCount\":${PASS}}"
    exit 1
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test_zurl.sh <zurl>\",\"discovered\":${DISCOVERED},\"passedCount\":${PASS}}"
exit 0
