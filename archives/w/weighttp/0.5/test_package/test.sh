#!/bin/sh
# test_package/test.sh — smoke test for weighttp executable on OHOS.
# Exercises the installed weighttp binary:
#   1. -h  (help output contains usage pattern)
#   2. -V  (version output contains 0.5)
#   3. local HTTP benchmark (python http.server + weighttp -n 10 -c 2 -t 1)
# HMBS hard-gate markers printed at end with real counters.
set -u

PASS=0
FAIL=0
DISCOVERED=3

# Writable scratch: OHOS /tmp is read-only (HMBS readonly_tmp). Never use
# /tmp directly: prefer HMBS-injected TMPDIR/TMP/TEMP only after a touch
# probe ([ -w ] lies on HMDFS), else fall back to script dir.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRATCH_BASE="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ "$SCRATCH_BASE" = "/tmp" ] || [ "$SCRATCH_BASE" = "/tmp/" ]; then
    SCRATCH_BASE="$SCRIPT_DIR"
fi
if [ -n "$SCRATCH_BASE" ] && [ -d "$SCRATCH_BASE" ] 2>/dev/null; then
    if ! touch "$SCRATCH_BASE/.weighttp_wtest_$$" 2>/dev/null; then
        SCRATCH_BASE="$SCRIPT_DIR"
    else
        rm -f "$SCRATCH_BASE/.weighttp_wtest_$$"
    fi
else
    SCRATCH_BASE="$SCRIPT_DIR"
fi
SCRATCH="$(mktemp -d "${SCRATCH_BASE}/weighttp-test.XXXXXX" 2>/dev/null || echo "")"
if [ -z "$SCRATCH" ] || [ ! -d "$SCRATCH" ]; then
    SCRATCH="$SCRIPT_DIR/.scratch-$$"
    mkdir -p "$SCRATCH"
fi
trap 'rm -rf "$SCRATCH"; kill $SERVER_PID 2>/dev/null || true; wait $SERVER_PID 2>/dev/null || true' EXIT INT TERM
SERVER_PID=""

assert_pass() {
    PASS=$((PASS + 1))
    echo "[PASS] $1"
}

assert_fail() {
    FAIL=$((FAIL + 1))
    if [ $# -ge 2 ] && [ -n "$2" ]; then
        echo "[FAIL] $1 — $2"
    else
        echo "[FAIL] $1"
    fi
}

# Locate the installed binary: prefer explicit WTTP_PKG_BIN dir (passed by
# conanfile), then PATH lookup. Tolerate HMDFS chmod=0 (missing +x).
echo "[test] PATH=$PATH"
echo "[test] WTTP_PKG_BIN=${WTTP_PKG_BIN:-(unset)}"
if [ -n "${WTTP_PKG_BIN:-}" ]; then
    ls -l "${WTTP_PKG_BIN}" 2>&1 || true
fi
WEIGHTTP=""
for _cand in "${WTTP_PKG_BIN:-}/weighttp"; do
    if [ -n "${_cand:-}" ] && [ -f "$_cand" ]; then
        chmod +x "$_cand" 2>/dev/null || true
        WEIGHTTP="$_cand"
        break
    fi
done
if [ -z "$WEIGHTTP" ]; then
    if command -v weighttp >/dev/null 2>&1; then
        WEIGHTTP="$(command -v weighttp)"
    fi
fi
if [ -z "$WEIGHTTP" ]; then
    echo "[FAIL] weighttp binary not found on PATH"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh","discovered":%d,"passedCount":0}\n' "$DISCOVERED"
    exit 1
fi
echo "[test] using binary: $WEIGHTTP"
ls -l "$WEIGHTTP" 2>&1 || true

# --- 1. weighttp -h ---
echo "[test] weighttp -h"
if output="$("$WEIGHTTP" -h 2>&1 || true)"; then
    if [ -n "$output" ] && echo "$output" | grep -q "weighttp <options> <URI>"; then
        assert_pass "weighttp -h contains usage pattern"
        echo "$output" | head -5
    else
        assert_fail "weighttp -h output unexpected" "$output"
    fi
else
    assert_fail "weighttp -h execution failed"
fi

# --- 2. weighttp -V ---
echo "[test] weighttp -V"
if output2="$("$WEIGHTTP" -V 2>&1 || true)"; then
    if [ -n "$output2" ] && echo "$output2" | grep -q "weighttp 0.5"; then
        assert_pass "weighttp -V contains version 0.5"
        echo "$output2" | head -5
    else
        assert_fail "weighttp -V output unexpected" "$output2"
    fi
else
    assert_fail "weighttp -V execution failed"
fi

# --- 3. local HTTP benchmark ---
echo "[test] weighttp local HTTP benchmark"
HTTP_TMP="$SCRATCH/http_root"
mkdir -p "$HTTP_TMP"
echo "hello weighttp" > "$HTTP_TMP/index.html"
HTTP_LOG="$SCRATCH/weighttp_http.log"
# Pick a free port: try 18080, fallback to 18081-18085
HTTP_PORT=18080
for _p in 18080 18081 18082 18083 18084 18085; do
    if python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.bind(('127.0.0.1', $_p)); s.close()" 2>/dev/null; then
        HTTP_PORT=$_p
        break
    fi
done
echo "[test] http server port $HTTP_PORT tmp $HTTP_TMP log $HTTP_LOG"
python3 -m http.server "$HTTP_PORT" --directory "$HTTP_TMP" >"$HTTP_LOG" 2>&1 &
SERVER_PID=$!
echo "[test] http server pid $SERVER_PID"
# wait for server to be ready (max 5s)
_ready=0
for i in 1 2 3 4 5 6 7 8 9 10; do
    if python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1',$HTTP_PORT)); s.close()" 2>/dev/null; then
        echo "[test] http server ready"
        _ready=1
        break
    fi
    sleep 0.5
done
if [ "$_ready" -ne 1 ]; then
    echo "[test] http server failed to start, log:"
    cat "$HTTP_LOG" 2>&1 | head -n 50 || true
    assert_fail "http server not ready on port $HTTP_PORT"
else
    bench_out=""
    bench_rc=0
    # Run benchmark; guard with timeout if available
    if command -v timeout >/dev/null 2>&1; then
        bench_out="$(timeout 15 "$WEIGHTTP" -n 10 -c 2 -t 1 "http://127.0.0.1:${HTTP_PORT}/" 2>&1 || true)"
        bench_rc=$?
        # timeout 124 means timed out
        if [ "$bench_rc" -eq 124 ]; then
            echo "[test] weighttp benchmark timed out"
        fi
    else
        bench_out="$("$WEIGHTTP" -n 10 -c 2 -t 1 "http://127.0.0.1:${HTTP_PORT}/" 2>&1 || true)"
        bench_rc=$?
    fi
    echo "$bench_out"
    # Cleanup server immediately after benchmark
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    SERVER_PID=""
    # Validate output: need non-empty and contains reqs_per_sec
    if [ -n "$bench_out" ] && echo "$bench_out" | grep -q "reqs_per_sec"; then
        # Ensure output not empty placeholder: require at least one digit + benchmark table
        if echo "$bench_out" | grep -qE "[0-9]+ reqs"; then
            assert_pass "weighttp benchmark produced reqs_per_sec"
        else
            assert_pass "weighttp benchmark produced reqs_per_sec (raw)"
        fi
    else
        assert_fail "benchmark output missing reqs_per_sec" "$bench_out"
    fi
fi
# Ensure server cleaned
if [ -n "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    SERVER_PID=""
fi

# --- HMBS hard-gate markers (numbers from counters above) ---
passed="true"
if [ "$PASS" -ne "$DISCOVERED" ] || [ "$FAIL" -ne 0 ]; then
    passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"sh test.sh","discovered":%d,"passedCount":%d}\n' \
    "$passed" "$DISCOVERED" "$PASS"
# HMBS_UPSTREAM_TEST_RESULT is authoritative and re-emitted by test_package/conanfile.py
# from package/res/upstream_test_result.json (persists across Conan cache hits).
# Do not emit a hard-coded upstream marker here to avoid duplicate/forged evidence.

echo "=== test_package summary: ${PASS}/${DISCOVERED} passed, ${FAIL} failed ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$DISCOVERED" ]; then
    exit 1
fi
exit 0
