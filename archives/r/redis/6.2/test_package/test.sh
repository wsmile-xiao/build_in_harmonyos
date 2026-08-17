#!/usr/bin/env bash
set -eu

REDIS_SERVER="${REDIS_SERVER:-redis-server}"
REDIS_CLI="${REDIS_CLI:-redis-cli}"
PORT=$((20000 + ($$ % 20000)))
WORK_ROOT="${TMPDIR:-$PWD}"
WORK_DIR="$WORK_ROOT/redis-test-$$"
PIDFILE="$WORK_DIR/redis.pid"
LOGFILE="$WORK_DIR/redis.log"

cleanup() {
    "$REDIS_CLI" -h 127.0.0.1 -p "$PORT" shutdown nosave >/dev/null 2>&1 || true
    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM
mkdir -p "$WORK_DIR"

server_version=$("$REDIS_SERVER" --version)
case "$server_version" in
    *"v=6.2.0"*) ;;
    *) echo "unexpected redis-server version: $server_version" >&2; exit 1 ;;
esac

cli_version=$("$REDIS_CLI" --version)
case "$cli_version" in
    *"6.2.0"*) ;;
    *) echo "unexpected redis-cli version: $cli_version" >&2; exit 1 ;;
esac

"$REDIS_SERVER" \
    --bind 127.0.0.1 \
    --protected-mode no \
    --port "$PORT" \
    --save "" \
    --appendonly no \
    --daemonize yes \
    --pidfile "$PIDFILE" \
    --dir "$WORK_DIR" \
    --logfile "$LOGFILE"

attempt=0
reply=""
while [ "$attempt" -lt 50 ]; do
    reply=$("$REDIS_CLI" -h 127.0.0.1 -p "$PORT" --raw ping 2>/dev/null || true)
    [ "$reply" = "PONG" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
[ "$reply" = "PONG" ] || {
    echo "redis-server did not become ready" >&2
    cat "$LOGFILE" >&2 || true
    exit 1
}

reply=$("$REDIS_CLI" -h 127.0.0.1 -p "$PORT" --raw set harmonyos redis-6.2.0)
[ "$reply" = "OK" ] || { echo "SET failed: $reply" >&2; exit 1; }

reply=$("$REDIS_CLI" -h 127.0.0.1 -p "$PORT" --raw get harmonyos)
[ "$reply" = "redis-6.2.0" ] || { echo "GET failed: $reply" >&2; exit 1; }

reply=$("$REDIS_CLI" -h 127.0.0.1 -p "$PORT" --raw del harmonyos)
[ "$reply" = "1" ] || { echo "DEL failed: $reply" >&2; exit 1; }

echo "redis 6.2.0 service test passed"
