#!/usr/bin/env bash
set -euo pipefail

chezdav_bin=$1
work_dir=$2

version_output=$("$chezdav_bin" --version)
test "$version_output" = "phodav 3.0"

help_output=$("$chezdav_bin" --help)
case "$help_output" in
  *"simple WebDAV server"*) ;;
  *)
    echo "chezdav help output did not describe the WebDAV server" >&2
    exit 1
    ;;
esac

share_dir="$work_dir/share"
mkdir -p "$share_dir"
printf 'chezdav-ohos-smoke\n' >"$share_dir/hello.txt"

port=$((18080 + ($$ % 1000)))
server_log="$work_dir/server.log"
"$chezdav_bin" --local --port "$port" --path "$share_dir" >"$server_log" 2>&1 &
server_pid=$!
cleanup() {
  kill "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 - "$port" <<'PY'
import http.client
import sys
import time

port = int(sys.argv[1])
last_error = None
for _ in range(50):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", "/hello.txt")
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise AssertionError("unexpected HTTP status {}".format(response.status))
        if body != b"chezdav-ohos-smoke\n":
            raise AssertionError("unexpected response body {!r}".format(body))
        break
    except (ConnectionError, OSError) as error:
        last_error = error
        time.sleep(0.1)
    finally:
        connection.close()
else:
    raise SystemExit("chezdav server did not become ready: {}".format(last_error))
PY

echo "chezdav runtime checks passed"
