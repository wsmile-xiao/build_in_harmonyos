#!/bin/bash
# test_package smoke test for miniserve 0.35.0
# Verifies the miniserve binary works: --version and a real HTTP serve + fetch.
set -euo pipefail

if [ -z "$MS_BIN" ]; then
    echo "ERROR: MS_BIN not set" >&2
    exit 1
fi

echo "== Test 1: miniserve --version =="
"$MS_BIN" --version

echo "== Test 2: serve a directory and fetch a file over HTTP =="
WORK=$(mktemp -d)
echo "hello-miniserve-0.35.0" > "$WORK/hello.txt"
PORT=18765
"$MS_BIN" "$WORK" --port "$PORT" --no-symlinks > "$WORK/server.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true; rm -rf "$WORK"' EXIT

# wait for the server to accept connections
OK=0
for i in $(seq 1 20); do
    if curl -s -o "$WORK/out.txt" "http://127.0.0.1:$PORT/hello.txt"; then
        OK=1
        break
    fi
    sleep 0.5
done
if [ "$OK" != "1" ]; then
    echo "ERROR: server did not answer" >&2
    cat "$WORK/server.log" >&2 || true
    exit 1
fi

echo "fetched content: $(cat "$WORK/out.txt")"
grep -q "hello-miniserve-0.35.0" "$WORK/out.txt"

echo "== Test 3: server log shows startup =="
head -3 "$WORK/server.log"

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo "miniserve test_package: PASS"
