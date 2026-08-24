#!/data/service/hnp/bin/bash
# test_package/test.sh — ttyd 1.7.7 consumer smoke test.
# Runs in the conanrun env (PATH includes the installed package's bin/).
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

echo "[test] ttyd binary is executable and versioned"
if ! command -v ttyd >/dev/null 2>&1; then
    fail "ttyd not found in PATH"
fi

echo "[test] ttyd --version"
VERSION_OUT=$(ttyd --version 2>&1) || fail "ttyd --version exited non-zero"
echo "  $VERSION_OUT"
echo "$VERSION_OUT" | grep -q "1.7.7" || fail "--version does not mention 1.7.7"

echo "[test] ttyd --help"
HELP_OUT=$(ttyd --help 2>&1) || fail "ttyd --help exited non-zero"
echo "$HELP_OUT" | grep -qi "usage" || fail "--help has no usage line"

echo "[test] ttyd -h (short help)"
H_OUT=$(ttyd -h 2>&1) || fail "ttyd -h exited non-zero"
[ -n "$H_OUT" ] || fail "-h produced no output"

echo "[test] ttyd minimal local server startup (offline)"
PORT=7681
TEST_LOG_DIR="${TMPDIR:-/tmp}"
TEST_LOG="$TEST_LOG_DIR/ttyd-test.log"
ttyd -p "$PORT" /bin/sh >"$TEST_LOG" 2>&1 &
SERVER_PID=$!
sleep 2
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "  server log:"; cat "$TEST_LOG" 2>/dev/null | head -5
    fail "ttyd server did not stay up"
fi
echo "  ttyd listening on port $PORT (pid $SERVER_PID)"
# 清理阶段：服务可能已自行退出，忽略 kill/wait 失败
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
rm -f "$TEST_LOG"

echo "ALL TESTS PASSED"
