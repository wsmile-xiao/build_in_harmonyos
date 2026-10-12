#!/usr/bin/env bash
# Run an IPv4 UDP STUN request against a local HarmonyOS server.
set -euo pipefail
echo "[step] Testing HarmonyOS IPv4 UDP STUN loopback..."

if [ "$#" -ne 2 ]; then
  echo "        [fail] usage: test_ohos_stun_loopback.sh <stund> <stunbdc>" >&2
  exit 2
fi

stund=$1
stunbdc=$2
if [ ! -x "$stund" ]; then
  echo "        [fail] STUN server is missing or not executable: $stund" >&2
  exit 2
fi
if [ ! -x "$stunbdc" ]; then
  echo "        [fail] STUN client is missing or not executable: $stunbdc" >&2
  exit 2
fi

server_pid=
cleanup () {
  if [ -n "$server_pid" ]; then
    # The server may have exited after handling the request, so cleanup can race.
    kill -TERM "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
    server_pid=
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

base_port=$((40000 + ($$ % 20000)))
attempt=0
while [ "$attempt" -lt 6 ]; do
  port=$((base_port + attempt))
  "$stund" -4 "$port" >/dev/null 2>&1 &
  server_pid=$!
  sleep 1

  if kill -0 "$server_pid" 2>/dev/null; then
    if output=$("$stunbdc" -4 -n 127.0.0.1 "$port" 2>&1); then
      case "$output" in
        *"Mapped address:"*)
          printf '%s\n' "$output"
          echo "        [ok] HarmonyOS IPv4 UDP STUN loopback passed on port $port"
          exit 0
          ;;
      esac
    fi
  fi

  cleanup
  attempt=$((attempt + 1))
done

echo "        [fail] STUN UDP loopback failed after $attempt local-port attempts" >&2
exit 1
