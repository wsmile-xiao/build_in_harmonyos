#!/bin/sh
# test_inspircd.sh — consumer functional test for the inspircd 4.7.0 package.
# Starts the packaged bin/inspircd with a minimal generated config, performs
# a real IRC handshake (NICK/USER -> 001 welcome) over TCP, then shuts the
# server down cleanly. Prints a machine-readable "RESULT: P passed, F failed"
# trailer line, which test_package/conanfile.py parses into
# HMBS_TEST_PACKAGE_RESULT.
#
# Every positive case asserts non-empty output plus exact expected content
# (toybox-tar lesson: never compare empty output against empty output).
# Negative control: case 5 asserts the port is really released after
# shutdown (a lingering process cannot masquerade as a pass).
# TCP is done via "${HMBS_PYTHON3:-python3}" (POSIX sh has no /dev/tcp);
# HMBS injects HMBS_PYTHON3 plus tool dirs on PATH.
#
# Env: INSPIRCD_BIN (server binary), INSPIRCD_MODDIR (packaged modules dir),
#      INSPIRCD_TEST_PORT (default 14661).

set -u

BIN="${INSPIRCD_BIN:-inspircd}"
MODDIR="${INSPIRCD_MODDIR:-}"
PORT="${INSPIRCD_TEST_PORT:-14661}"
PY="${HMBS_PYTHON3:-python3}"
# Device /tmp may be read-only: prefer the HMBS-injected writable
# TMPDIR/TMP/TEMP, fall back to the current directory (never /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
TESTDIR="$_TMPBASE/inspircd-test-$$"
OUT="$_TMPBASE/inspircd-test-out.txt"
PASS=0
FAIL=0
SERVER_PID=""

report() {
    # $1 = case number, $2 = ok (0/1), $3 = label
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    # $1 = exit code; print bounded output excerpt for diagnosis.
    echo "  exit=$1, output excerpt (first 15 lines):"
    head -n 15 "$OUT" 2>/dev/null || echo "  (no output file)"
}

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        SERVER_PID=""
    fi
    rm -rf "$TESTDIR"
}
trap cleanup EXIT INT TERM

mkdir -p "$TESTDIR" || {
    echo "CASE 0 FAIL: cannot create $TESTDIR"
    echo "RESULT: 0 passed, 1 failed"
    exit 1
}

# Case 1: binary present, executable, non-empty.
if [ -x "$BIN" ] && [ -s "$BIN" ]; then
    report 1 0 "inspircd binary present, executable and non-empty"
else
    report 1 1 "inspircd binary missing/not-executable/empty: $BIN"
fi

# Case 2: --version prints a non-empty banner mentioning InspIRCd-4.7.0.
"$BIN" --version > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s "$OUT" ] && grep -q "InspIRCd-4.7.0" "$OUT"; then
    report 2 0 "inspircd --version reports InspIRCd-4.7.0"
else
    dump_out $rc
    report 2 1 "inspircd --version failed (exit=$rc, no InspIRCd-4.7.0 banner)"
fi

# Resolve the module dir (core_*.so auto-load from here at startup).
if [ -z "$MODDIR" ]; then
    MODDIR="$(dirname "$BIN")/../modules"
fi
if [ -d "$MODDIR" ]; then
    nmod=$(ls "$MODDIR"/core_*.so 2>/dev/null | wc -l)
else
    nmod=0
fi
echo "  moduledir=$MODDIR core_modules=$nmod"

# Case 3: server starts and listens on 127.0.0.1:$PORT.
cat > "$TESTDIR/inspircd.conf" <<EOF
<server name="hmbs-test.local"
        description="HMBS preflight test server"
        network="HMBSTest">
<admin name="HMBS Tester"
       description="preflight"
       email="hmbs@localhost">
<bind address="127.0.0.1"
      port="$PORT"
      type="clients">
<pid file="$TESTDIR/inspircd.pid">
<log method="file"
     level="normal"
     type="* -USERINPUT -USEROUTPUT"
     target="$TESTDIR/inspircd.log">
<path moduledir="$MODDIR"
      configdir="$TESTDIR"
      datadir="$TESTDIR"
      logdir="$TESTDIR">
EOF

"$BIN" --config "$TESTDIR/inspircd.conf" --nofork --nolog --nopid --runasroot > "$TESTDIR/server.out" 2>&1 &
SERVER_PID=$!
echo "  server pid=$SERVER_PID"

if ! command -v "$PY" >/dev/null 2>&1 && [ ! -x "$PY" ]; then
    PY=python3
fi
ready=0
i=0
while [ $i -lt 60 ]; do
    if "$PY" -c "import socket,sys; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',$PORT)); s.close()" >/dev/null 2>&1; then
        ready=1
        break
    fi
    # Server died early? Do not wait the full 30 s on a dead process.
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        break
    fi
    sleep 0.5
    i=$((i + 1))
done
if [ "$ready" -eq 1 ]; then
    report 3 0 "server listening on 127.0.0.1:$PORT (pid $SERVER_PID)"
else
    echo "  --- server.out (last 15 lines) ---"
    tail -n 15 "$TESTDIR/server.out" 2>/dev/null || echo "  (no server output)"
    echo "  --- $TESTDIR/inspircd.log (last 15 lines) ---"
    tail -n 15 "$TESTDIR/inspircd.log" 2>/dev/null || echo "  (no log file)"
    report 3 1 "server did not listen on port $PORT"
fi

# Case 4: real IRC handshake (NICK/USER -> 001 welcome, then QUIT).
if [ "$ready" -eq 1 ]; then
    "$PY" - "$PORT" > "$OUT" 2>&1 <<'PYEOF'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(20)
s.connect(('127.0.0.1', port))
f = s.makefile('r', encoding='utf-8', errors='replace')
s.sendall(b'NICK hmbs01\r\nUSER hmbs 0 * :HMBS Test\r\n')
got001 = False
lines = []
try:
    while True:
        line = f.readline()
        if not line:
            break
        line = line.rstrip('\r\n')
        lines.append(line)
        print(line)
        if ' 001 ' in line and 'hmbs01' in line:
            got001 = True
            break
        if len(lines) > 40:
            break
finally:
    try:
        s.sendall(b'QUIT :test done\r\n')
    except OSError:
        pass
    s.close()
print('GOT001=%s' % got001)
sys.exit(0 if got001 else 1)
PYEOF
    rc=$?
    if [ $rc -eq 0 ] && [ -s "$OUT" ] && grep -q "GOT001=True" "$OUT" && grep -q " 001 hmbs01 " "$OUT"; then
        report 4 0 "IRC handshake: server issued 001 welcome to hmbs01"
    else
        dump_out $rc
        report 4 1 "IRC handshake failed (exit=$rc, no 001 welcome)"
    fi
else
    report 4 1 "IRC handshake skipped (server not listening)"
fi

# Case 5: clean shutdown releases the port (negative control).
if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    SERVER_PID=""
    sleep 1
fi
if "$PY" -c "import socket,sys; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',$PORT)); s.close()" >/dev/null 2>&1; then
    report 5 1 "port $PORT still open after shutdown (server lingered)"
else
    report 5 0 "clean shutdown, port $PORT released"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
