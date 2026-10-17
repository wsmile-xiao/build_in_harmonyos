#!/data/service/hnp/bin/bash
# test_package/test.sh — ngircd 28 smoke tests (headless daemon)
# Runs in conanrun env (PATH includes installed bin/)
# 3 test groups: version / configtest / daemon+raw-socket welcome.
set -u

BIN=ngircd
PORT=16667
CONF="$(pwd)/ngircd-test.conf"
LOG="$(pwd)/ngircd-test.log"
PYTHON="${PYTHON:-/data/service/hnp/bin/python3}"
failures=0

echo "== [1/3] version check =="
# NOTE: upstream ngircd -V prints version then exit(1) by design
# (src/ngircd/ngircd.c "case 'V': Show_Version(); exit(1);");
# assert on output only, ignore the exit code.
"$BIN" -V > version.txt 2>&1
cat version.txt
if grep -qi "ngircd 28" version.txt; then
    echo "PASS: ngircd -V output contains 'ngircd 28'"
else
    echo "FAIL: unexpected version output"
    failures=$((failures+1))
fi

echo "== [2/3] --configtest (config validation) =="
# ngircd refuses to run as root(0) and then looks up "nobody", which does
# not exist in the OHOS /etc/passwd; pin ServerUID/ServerGID to the current
# (already unprivileged) user so the privilege-drop branch is skipped.
UID_NUM=$("$PYTHON" -c "import os; print(os.getuid())")
GID_NUM=$("$PYTHON" -c "import os; print(os.getgid())")
cat > "$CONF" <<EOF
[Global]
	Name = TestServer.OpenDesk
	AdminInfo1 = OpenDesk Test
	AdminInfo2 = HarmonyOS
	AdminEMail = test@opendesk.local
	Listen = 127.0.0.1
	Ports = $PORT
	ServerUID = $UID_NUM
	ServerGID = $GID_NUM
EOF
"$BIN" --configtest --config "$CONF" > configtest.log 2>&1
rc=$?
cat configtest.log
if [ $rc -eq 0 ]; then
    echo "PASS: --configtest exit 0"
else
    echo "FAIL: --configtest exit $rc"
    failures=$((failures+1))
fi

echo "== [3/3] daemon smoke on 127.0.0.1:$PORT =="
"$BIN" --nodaemon --config "$CONF" > "$LOG" 2>&1 &
DAEMON_PID=$!
sleep 2
"$PYTHON" - "$PORT" <<'PYEOF'
import socket
import sys
import time

port = int(sys.argv[1])
try:
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(b"NICK tester\r\nUSER tester 0 * :Test User\r\n")
    data = b""
    deadline = time.time() + 5
    while time.time() < deadline and b"001" not in data:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    s.close()
    if b"001" in data:
        print("PASS: received numeric 001 welcome")
        sys.exit(0)
    print("FAIL: no 001 welcome; got:", data[:200])
    sys.exit(1)
except Exception as exc:
    print("FAIL: socket error:", exc)
    sys.exit(1)
PYEOF
PYRC=$?
if [ $PYRC -eq 0 ]; then
    echo "PASS: daemon accepted raw NICK/USER and sent 001"
else
    echo "FAIL: daemon smoke (python rc=$PYRC); daemon log tail:"
    tail -20 "$LOG" 2>/dev/null
    failures=$((failures+1))
fi

# normal shutdown
kill "$DAEMON_PID" 2>/dev/null
wait "$DAEMON_PID" 2>/dev/null
echo "daemon stopped (pid $DAEMON_PID)"

if [ $failures -eq 0 ]; then
    echo ""
    echo "ALL TESTS PASSED"
    exit 0
fi
echo ""
echo "$failures TEST GROUP(S) FAILED"
exit 1
