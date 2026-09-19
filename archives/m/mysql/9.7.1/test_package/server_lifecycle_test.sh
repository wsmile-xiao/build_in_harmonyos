#!/bin/sh
# mysql/9.7.1 server lifecycle test: initialize -> start -> ping -> shutdown.
# Every step must exit 0; the script exits non-zero on the first failure.
# NOTE: /bin/sh (POSIX) on purpose — CI workers have no bash (/bin/bash bad
# interpreter, same class as mussh). Only POSIX constructs are used below.
#
# Transport: TCP only. OHOS sandboxes deny bind() on AF_UNIX paths (EPERM), so
# the server is started with --socket= (Unix socket disabled) and the client
# tools connect through -h127.0.0.1 -P<port>; patch 0070 makes the server
# degrade to TCP-only listening instead of aborting in that situation.
set -u

BIN="${MYSQLD_BIN_DIR:?MYSQLD_BIN_DIR must point to the package bin/}"
WORK="${MYSQLD_TEST_DIR:-${TMPDIR:-/tmp}/mysql971-test}"
PORT="${MYSQLD_TEST_PORT:-33207}"

mkdir -p "$WORK" || { echo "cannot create $WORK"; exit 1; }
rm -rf "$WORK/data" "$WORK/mysql.sock" "$WORK/mysql.pid" "$WORK/err.log"
mkdir -p "$WORK/data"

echo "==[1] mysqld --initialize-insecure =="
"$BIN/mysqld" --no-defaults --initialize-insecure \
  --basedir="$BIN/.." \
  --datadir="$WORK/data" \
  --log-error="$WORK/init.log"
INIT_RC=$?
echo "init rc=$INIT_RC"
if [ "$INIT_RC" -ne 0 ]; then cat "$WORK/init.log" 2>/dev/null | tail -20; exit "$INIT_RC"; fi

echo "==[2] mysqld start (background, TCP only) =="
"$BIN/mysqld" --no-defaults \
  --basedir="$BIN/.." \
  --datadir="$WORK/data" \
  --socket= \
  --pid-file="$WORK/mysql.pid" \
  --port="$PORT" \
  --skip-networking=0 \
  --log-bin-trust-function-creators=1 \
  --log-error="$WORK/err.log" &
MYSQLD_PID=$!
echo "mysqld pid=$MYSQLD_PID"

# Wait up to 60s for the server to accept connections over TCP.
ok=""
i=1
while [ "$i" -le 60 ]; do
  if "$BIN/mysqladmin" --no-defaults -h127.0.0.1 -P"$PORT" --user=root ping >/dev/null 2>&1; then
    ok=1
    break
  fi
  if ! kill -0 "$MYSQLD_PID" 2>/dev/null; then
    echo "mysqld died early"
    tail -30 "$WORK/err.log" 2>/dev/null
    exit 1
  fi
  sleep 1
  i=$((i + 1))
done
if [ -z "$ok" ]; then
  echo "server did not accept TCP connections within 60s"
  tail -30 "$WORK/err.log" 2>/dev/null
  kill "$MYSQLD_PID" 2>/dev/null
  exit 1
fi

echo "==[3] mysqladmin ping =="
"$BIN/mysqladmin" --no-defaults -h127.0.0.1 -P"$PORT" --user=root ping
PING_RC=$?
echo "ping rc=$PING_RC"
if [ "$PING_RC" -ne 0 ]; then
  tail -30 "$WORK/err.log" 2>/dev/null
  kill "$MYSQLD_PID" 2>/dev/null
  exit "$PING_RC"
fi

echo "==[4] mysqladmin shutdown =="
"$BIN/mysqladmin" --no-defaults -h127.0.0.1 -P"$PORT" --user=root shutdown
SHUT_RC=$?
echo "shutdown rc=$SHUT_RC"
wait "$MYSQLD_PID" 2>/dev/null
WAIT_RC=$?
echo "mysqld wait rc=$WAIT_RC"

if [ "$SHUT_RC" -ne 0 ]; then exit "$SHUT_RC"; fi
# A clean shutdown normally exits 0.
if [ "$WAIT_RC" -ne 0 ]; then exit "$WAIT_RC"; fi

echo "== server lifecycle test PASSED =="
exit 0
