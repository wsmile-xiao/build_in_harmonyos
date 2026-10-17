#!/usr/bin/env bash
# test_package/test.sh — functional tests for the proxytunnel binary.
# Runs in conanrun env (PATH includes the installed bin/); conanfile.py
# invokes it as `bash test.sh`, so the shebang is not relied upon at runtime.
# R34: every assertion genuinely invokes the tested binary and verifies real
# behaviour (network round-trip through a local mock proxy included).
# Temp files are CWD-relative (no $HOME / absolute paths; /tmp is read-only
# on OHOS).
set -u

PASS=0
FAIL=0
ok()  { PASS=$((PASS+1)); echo "OK: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

PY="$(command -v python3 || command -v python || true)"

# --------------------------------------------------------------- find binary
PT="$(command -v proxytunnel || true)"
if [ -z "$PT" ]; then
    echo "FAIL: proxytunnel binary not found on PATH"
    exit 1
fi
echo "using binary: $PT"

# ------------------------------------------------------------ 1: version (-V)
V="$("$PT" -V 2>&1)"
case "$V" in
    *"proxytunnel 1.13.0"*) ok "-V prints version banner 1.13.0";;
    *) bad "-V unexpected output: $V";;
esac

# ------------------------------------------------------------ 2: help (usage)
H="$("$PT" --help 2>&1)"
case "$H" in
    *"Usage: proxytunnel"*) ok "--help prints usage";;
    *) bad "--help unexpected: $H";;
esac
case "$H" in
    *--encrypt-proxy*) ok "--help documents SSL tunnel options (-E)";;
    *) bad "--help missing SSL options (-E)";;
esac

# --------------------------------------------- 3+4: real CONNECT tunnel (mock)
# Mock proxy: accepts one connection, waits for the CONNECT request, replies
# "200 Connection established", then echoes tunneled payload back with a
# prefix. The request/payload are logged to mock_stderr.txt for assertions.
if [ -n "$PY" ]; then
    "$PY" - <<'MOCKEOF' > mock_port.txt 2> mock_stderr.txt &
import socket, sys, time
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0))
print(srv.getsockname()[1], flush=True)
srv.listen(1)
srv.settimeout(30)
c, _ = srv.accept()
c.settimeout(10)
data = b""
while b"\r\n\r\n" not in data:
    try:
        chunk = c.recv(4096)
    except Exception:
        chunk = b""
    if not chunk:
        break
    data += chunk
sys.stderr.write("REQ:%s\n" % data.decode(errors="replace"))
if data.startswith(b"CONNECT example.org:443"):
    c.sendall(b"HTTP/1.0 200 Connection established\r\n\r\n")
    try:
        payload = c.recv(4096)
    except Exception:
        payload = b""
    sys.stderr.write("TUN:%s\n" % payload.decode(errors="replace"))
    c.sendall(b"MOCK-ECHO:" + payload)
time.sleep(1)
c.close(); srv.close()
MOCKEOF
    MOCK_PID=$!
    PORT=""
    for _ in $(seq 1 50); do
        [ -s mock_port.txt ] && { PORT=$(cat mock_port.txt); break; }
        sleep 0.1
    done
    if [ -n "$PORT" ]; then
        # keep stdin open for 2s after sending PING so the echo can come back
        # (proxytunnel exits as soon as stdin EOFs)
        OUT="$( { printf 'PING'; sleep 2; } | "$PT" -q -p 127.0.0.1:$PORT -d example.org:443 2>&1 )"
        case "$OUT" in
            *MOCK-ECHO:PING*) ok "data round-trip through CONNECT tunnel";;
            *) bad "tunnel round-trip failed, output: $OUT";;
        esac
        wait $MOCK_PID 2>/dev/null
        REQ_LINE="$(grep -a '^REQ:' mock_stderr.txt | head -1)"
        case "$REQ_LINE" in
            *"CONNECT example.org:443 HTTP/1.1"*) ok "CONNECT request format is correct";;
            *) bad "CONNECT request unexpected: $REQ_LINE";;
        esac
        TUN_LINE="$(grep -a '^TUN:' mock_stderr.txt | head -1)"
        case "$TUN_LINE" in
            *PING*) ok "stdin data forwarded through the tunnel";;
            *) bad "tunneled data unexpected: $TUN_LINE";;
        esac
    else
        bad "mock proxy failed to start"
        kill $MOCK_PID 2>/dev/null
    fi
else
    bad "python3 not available for mock proxy"
fi

# ------------------------------------------- 5: SSL path really linked (-e)
# Mock replies 200 but never speaks TLS -> SSL_connect must fail with a
# libssl error, proving the binary is genuinely linked against OpenSSL.
if [ -n "$PY" ]; then
    "$PY" - <<'MOCKEOF' > mock_port2.txt 2>/dev/null &
import socket, time
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0))
print(srv.getsockname()[1], flush=True)
srv.listen(1)
srv.settimeout(30)
c, _ = srv.accept()
c.settimeout(10)
data = b""
while b"\r\n\r\n" not in data:
    try:
        chunk = c.recv(4096)
    except Exception:
        chunk = b""
    if not chunk:
        break
    data += chunk
if data.startswith(b"CONNECT"):
    c.sendall(b"HTTP/1.0 200 Connection established\r\n\r\n")
    time.sleep(2)  # never complete a TLS handshake
c.close(); srv.close()
MOCKEOF
    MOCK2_PID=$!
    PORT2=""
    for _ in $(seq 1 50); do
        [ -s mock_port2.txt ] && { PORT2=$(cat mock_port2.txt); break; }
        sleep 0.1
    done
    if [ -n "$PORT2" ]; then
        OUT="$( { sleep 4; } | "$PT" -e -p 127.0.0.1:$PORT2 -d example.org:443 2>&1 )"
        RC=$?
        case "$OUT" in
            *SSL_connect*) ok "-e exercises the OpenSSL code path (SSL_connect attempted, rc=$RC)";;
            *) bad "-e did not reach SSL_connect, output: $OUT";;
        esac
        kill $MOCK2_PID 2>/dev/null
        wait $MOCK2_PID 2>/dev/null
    else
        bad "SSL mock proxy failed to start"
        kill $MOCK2_PID 2>/dev/null
    fi
fi

# --------------------------------------------- 6: connection-refused error path
OUT="$("$PT" -p 127.0.0.1:1 -d example.org:443 2>&1)"
RC=$?
case "$OUT" in
    *"failed to connect to local proxy"*) ok "connection-refused handled with clear error (rc=$RC)";;
    *) bad "refused-connection output unexpected: $OUT";;
esac

# ------------------------------------------------------------------- summary
echo "----"
echo "PASS=$PASS FAIL=$FAIL"
rm -f mock_port.txt mock_port2.txt mock_stderr.txt
[ "$FAIL" -eq 0 ] || exit 1
exit 0
