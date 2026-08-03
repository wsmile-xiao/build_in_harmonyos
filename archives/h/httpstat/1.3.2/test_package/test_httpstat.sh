#!/data/service/hnp/bin/bash
set -eu

HTTPSTAT_BIN="$1"

if [ ! -f "$HTTPSTAT_BIN" ]; then
    echo "FAIL: packaged httpstat command was not found"
    exit 1
fi
echo "PASS: packaged command exists"

version_output=$("$HTTPSTAT_BIN" --version)
if [ "$version_output" != "httpstat 1.3.2" ]; then
    echo "FAIL: unexpected version output: $version_output"
    exit 1
fi
echo "PASS: version output"

help_output=$("$HTTPSTAT_BIN" --help)
case "$help_output" in
    *"Usage: httpstat URL [CURL_OPTIONS]"*) ;;
    *)
        echo "FAIL: help output does not contain the usage line"
        exit 1
        ;;
esac
echo "PASS: help output"

set +e
invalid_output=$("$HTTPSTAT_BIN" https://example.invalid -w "%{http_code}" 2>&1)
invalid_status=$?
set -e

if [ "$invalid_status" -ne 1 ]; then
    echo "FAIL: forbidden curl option returned status $invalid_status"
    exit 1
fi
echo "PASS: forbidden curl option exit status"

case "$invalid_output" in
    *"is not allowed in extra curl args"*) ;;
    *)
        echo "FAIL: forbidden curl option message was not reported"
        exit 1
        ;;
esac
echo "PASS: forbidden curl option message"

TEST_TMP_ROOT="${TMPDIR:-${HOME}/tmp}"
TEST_TMP_DIR="$TEST_TMP_ROOT/httpstat-test-$$"
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$TEST_TMP_DIR"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$TEST_TMP_DIR"
printf '%s\n' "httpstat fixture body" > "$TEST_TMP_DIR/fixture.txt"

fixture_port=$((20000 + ($$ % 20000)))
python3 -m http.server "$fixture_port" \
    --bind 127.0.0.1 \
    --directory "$TEST_TMP_DIR" \
    > "$TEST_TMP_DIR/server.log" 2>&1 &
SERVER_PID=$!

fixture_ready=false
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
    if python3 -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1).read()' \
        "http://127.0.0.1:$fixture_port/fixture.txt" >/dev/null 2>&1; then
        fixture_ready=true
        break
    fi
    sleep 1
done

if [ "$fixture_ready" != true ]; then
    echo "FAIL: local HTTP fixture did not start"
    cat "$TEST_TMP_DIR/server.log"
    exit 1
fi
echo "PASS: local HTTP fixture responds"

set +e
core_output=$(PATH="$(dirname "$(command -v python3)")" \
    HTTPSTAT_CURL_BIN="$TEST_TMP_DIR/no-curl" \
    HTTPSTAT_SHOW_BODY=true HTTPSTAT_SAVE_BODY=false \
    "$HTTPSTAT_BIN" "http://127.0.0.1:$fixture_port/fixture.txt" 2>&1)
core_status=$?
set -e

if [ "$core_status" -ne 0 ]; then
    echo "FAIL: local HTTP request returned status $core_status"
    echo "$core_output"
    exit 1
fi
echo "PASS: local HTTP request exit status"

case "$core_output" in
    *"Connected to"*) ;;
    *)
        echo "FAIL: connection metrics were not rendered"
        exit 1
        ;;
esac
echo "PASS: connection metrics rendered"

case "$core_output" in
    *"HTTP/1.0 200 OK"*) ;;
    *)
        echo "FAIL: response headers were not rendered"
        exit 1
        ;;
esac
echo "PASS: response headers rendered"

case "$core_output" in
    *"httpstat fixture body"*) ;;
    *)
        echo "FAIL: response body was not rendered"
        exit 1
        ;;
esac
echo "PASS: response body rendered"

case "$core_output" in
    *"DNS Lookup"*"total:"*) ;;
    *)
        echo "FAIL: timing chart was not rendered"
        exit 1
        ;;
esac
echo "PASS: timing chart rendered"
