#!/usr/bin/env bash
# test.sh — gkrellm 2.3.11 test_package
# Exercise the packaged daemon's command and local TCP server paths.
set -euo pipefail

gkrellmd --version 2>&1 | grep -Eq '^gkrellmd [0-9]+\.[0-9]+'
gkrellmd --help 2>&1 | grep -qi 'usage'

port=$((20000 + ($$ % 10000)))
log="gkrellmd-${port}.log"
gkrellmd --address 127.0.0.1 --port "$port" --max-clients 1 >"$log" 2>&1 &
daemon_pid=$!
cleanup() {
    kill "$daemon_pid" 2>/dev/null || true
    wait "$daemon_pid" 2>/dev/null || true
    rm -f "$log"
}
trap cleanup EXIT

connected=false
for ((attempt = 0; attempt < 10; ++attempt)); do
    if bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        connected=true
        break
    fi
    sleep 1
done

test "$connected" = true
kill -0 "$daemon_pid"
echo "gkrellmd daemon TCP self-test passed"
