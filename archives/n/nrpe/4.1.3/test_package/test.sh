#!/data/service/hnp/bin/bash
# test_package/test.sh — nrpe 4.1.3 smoke tests (headless daemon + check_nrpe client)
# Runs in conanrun env (PATH includes installed bin/).
# 3 test groups: version / daemon+client connectivity / remote command execution.
# All runtime files (cfg/log/pid/client/cmd output) go to a private temp workdir so
# the tracked recipe tree stays clean.
set -u

BIN=nrpe
CLIENT=check_nrpe
PORT=$((15000 + ($$ % 20000)))
WORK="$(mktemp -d "${TMPDIR:-/tmp}/nrpe-test.XXXXXX")"
CONF="$WORK/nrpe-test.cfg"
LOG="$WORK/nrpe-test.log"
PYTHON="${PYTHON:-/data/service/hnp/bin/python3}"
failures=0

echo "workdir: $WORK"

echo "== [1/3] version check =="
"$BIN" -V > "$WORK/version.txt" 2>&1
cat "$WORK/version.txt"
if grep -qi "NRPE" "$WORK/version.txt" && grep -qi "4.1.3" "$WORK/version.txt"; then
    echo "PASS: nrpe -V output contains 'NRPE 4.1.3'"
else
    echo "FAIL: unexpected version output"
    failures=$((failures+1))
fi

echo "== [2/3] daemon on 127.0.0.1:$PORT + check_nrpe connectivity (no SSL) =="
# nrpe drop_privileges() accepts numeric uid/gid directly (no getpwnam lookup)
# and refuses to run as root (check_privileges). The sandbox euid may have no
# /etc/passwd entry, so use numeric ids of the current process.
UID_NUM=$("$PYTHON" -c "import os; print(os.getuid())")
GID_NUM=$("$PYTHON" -c "import os; print(os.getgid())")
cat > "$CONF" <<EOF
log_facility=daemon
pid_file=$WORK/nrpe-test.pid
server_port=$PORT
nrpe_user=$UID_NUM
nrpe_group=$GID_NUM
allowed_hosts=127.0.0.1
command[check_echo]=/data/service/hnp/bin/bash -c 'echo ok'
EOF
"$BIN" -f -n -c "$CONF" > "$LOG" 2>&1 &
DAEMON_PID=$!
sleep 2
"$CLIENT" -H 127.0.0.1 -p "$PORT" -n > "$WORK/client.txt" 2>&1
CLIENT_RC=$?
cat "$WORK/client.txt"
if [ $CLIENT_RC -eq 0 ] && grep -qi "NRPE" "$WORK/client.txt"; then
    echo "PASS: check_nrpe connected and received daemon version"
else
    echo "FAIL: check_nrpe rc=$CLIENT_RC; daemon log tail:"
    tail -20 "$LOG" 2>/dev/null
    failures=$((failures+1))
fi

echo "== [3/3] remote command execution via command[check_echo] =="
"$CLIENT" -H 127.0.0.1 -p "$PORT" -n -c check_echo > "$WORK/cmd.txt" 2>&1
CMD_RC=$?
cat "$WORK/cmd.txt"
if [ $CMD_RC -eq 0 ] && grep -q "ok" "$WORK/cmd.txt"; then
    echo "PASS: daemon executed command[check_echo] and returned its output"
else
    echo "FAIL: command execution rc=$CMD_RC; daemon log tail:"
    tail -20 "$LOG" 2>/dev/null
    failures=$((failures+1))
fi

# normal shutdown
kill -INT "$DAEMON_PID" 2>/dev/null
sleep 1
kill -TERM "$DAEMON_PID" 2>/dev/null
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
