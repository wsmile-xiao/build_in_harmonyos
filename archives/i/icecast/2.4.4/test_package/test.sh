#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the icecast server.
# Runs inside the conanrun env (PATH includes the installed bin/ and
# LD_LIBRARY_PATH includes conan-managed dependency libraries).
set -uo pipefail

PORT="${ICECAST_TEST_PORT:-18080}"
SCRATCH="${TMPDIR:-$HOME/tmp}"
mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/icecast-test-$$"
mkdir -p "$TESTDIR"
trap 'kill ${ICECAST_PID:-} 2>/dev/null; wait ${ICECAST_PID:-} 2>/dev/null; rm -rf "$TESTDIR"' EXIT

# ── Test 1: binary executes and reports version ──
echo "[test] icecast --version"
icecast --version | grep -q "Icecast 2.4.4" || {
    echo "❌ icecast --version did not report 'Icecast 2.4.4'"
    exit 1
}
echo "✅ --version OK"

# Locate webroot / adminroot from the installed package (share/icecast)
WEBROOT="$(dirname "$(command -v icecast)")/../share/icecast/web"
ADMINROOT="$(dirname "$(command -v icecast)")/../share/icecast/admin"
[ -f "$WEBROOT/status.xsl" ] || {
    echo "❌ status.xsl not found under $WEBROOT"
    exit 1
}

# ── Test 2: start minimal server and verify XSLT-rendered status page ──
cat > "$TESTDIR/icecast.xml" <<EOF
<icecast>
    <limits><sources>2</sources><clients>4</clients></limits>
    <authentication>
        <source-password>hackme</source-password>
        <relay-password>hackme</relay-password>
        <admin-user>admin</admin-user>
        <admin-password>hackme</admin-password>
    </authentication>
    <hostname>localhost</hostname>
    <listen-socket><port>$PORT</port></listen-socket>
    <fileserve>1</fileserve>
    <paths>
        <logdir>$TESTDIR</logdir>
        <webroot>$WEBROOT</webroot>
        <adminroot>$ADMINROOT</adminroot>
        <alias source="/" destination="/status.xsl"/>
    </paths>
    <logging>
        <accesslog>access.log</accesslog>
        <errorlog>error.log</errorlog>
        <loglevel>3</loglevel>
    </logging>
</icecast>
EOF

echo "[test] starting icecast -c $TESTDIR/icecast.xml"
icecast -c "$TESTDIR/icecast.xml" &
ICECAST_PID=$!

# Wait for the server to accept connections (up to ~15s)
ready=0
for i in $(seq 1 30); do
    if (echo > /dev/tcp/127.0.0.1/$PORT) 2>/dev/null; then
        ready=1
        break
    fi
    sleep 0.5
done
if [ "$ready" -ne 1 ]; then
    echo "❌ icecast did not listen on port $PORT"
    echo "--- error.log ---"
    cat "$TESTDIR/error.log" 2>/dev/null || true
    exit 1
fi
echo "✅ server listening on port $PORT"

# Request the status page; icecast renders it via libxslt XSLT
echo "[test] GET /status.xsl"
STATUS_HTTP="$(curl -s -o "$TESTDIR/status.html" -w '%{http_code}' "http://127.0.0.1:$PORT/status.xsl")"
if [ "$STATUS_HTTP" != "200" ]; then
    echo "❌ /status.xsl returned HTTP $STATUS_HTTP (expected 200)"
    exit 1
fi
grep -qi "icecast" "$TESTDIR/status.html" || {
    echo "❌ status page does not contain 'icecast' (XSLT render failed)"
    cat "$TESTDIR/status.html" | head -20
    exit 1
}
echo "✅ XSLT-rendered status page served ($(wc -c < "$TESTDIR/status.html") bytes)"

# ── Test 3: clean shutdown ──
echo "[test] shutting down"
kill "$ICECAST_PID" 2>/dev/null
wait "$ICECAST_PID" 2>/dev/null
ICECAST_PID=""
sleep 1
if (echo > /dev/tcp/127.0.0.1/$PORT) 2>/dev/null; then
    echo "❌ port $PORT still open after clean shutdown"
    exit 1
fi
echo "✅ clean shutdown, port released"

echo "ALL TESTS PASSED"
