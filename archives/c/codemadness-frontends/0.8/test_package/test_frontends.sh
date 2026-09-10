#!/data/service/hnp/bin/bash
# test_package/test_frontends.sh — offline smoke tests for the packaged
# codemadness-frontends binaries. Runs inside the conanrun env (PATH
# includes the installed bin/). No network access: all four assertions use
# offline code paths (usage handling, empty-query page rendering).
set -euo pipefail

# Resolve the binaries: $YOUTUBE_CLI etc. if set, otherwise from PATH.
CLI_BIN="${YOUTUBE_CLI:-youtube-cli}"
CGI_BIN="${YOUTUBE_CGI:-youtube-cgi}"
GOPHER_BIN="${YOUTUBE_GOPHER:-youtube-gopher}"
FEED_BIN="${YOUTUBE_FEED:-youtube-feed}"

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# --- scratch dir (OHOS /tmp may be read-only; use $TMPDIR) ---------------
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/frontends-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# --- Test 1: youtube-cli with no args prints usage, exits 1 --------------
echo "[test] youtube-cli (no args) prints usage"
OUT="$TESTDIR/cli-usage.out"
set +e
"$CLI_BIN" >"$OUT" 2>&1
RC1=$?
set -e
if [ "$RC1" -eq 0 ]; then
    fail "youtube-cli with no args unexpectedly exited 0"
else
    if grep -qi "usage:" "$OUT"; then
        pass "youtube-cli no-args prints usage (exit $RC1)"
    else
        fail "youtube-cli no-args output lacks usage:"
        cat "$OUT" || true
    fi
fi

# --- Test 2: youtube-cli -o bogus prints usage, exits non-zero ------------
echo "[test] youtube-cli -o bogus prints usage"
OUT2="$TESTDIR/cli-badopt.out"
set +e
"$CLI_BIN" -o bogus >"$OUT2" 2>&1
RC2=$?
set -e
if [ "$RC2" -eq 0 ]; then
    fail "youtube-cli -o bogus unexpectedly exited 0"
else
    if grep -qi "usage:" "$OUT2"; then
        pass "youtube-cli -o bogus prints usage (exit $RC2)"
    else
        fail "youtube-cli -o bogus output lacks usage:"
        cat "$OUT2" || true
    fi
fi

# --- Test 3: youtube-cgi with empty QUERY_STRING renders page -------------
echo "[test] youtube-cgi (empty QUERY_STRING) renders search page"
OUT3="$TESTDIR/cgi-empty.out"
if QUERY_STRING="" "$CGI_BIN" >"$OUT3" 2>"$TESTDIR/cgi-empty.err"; then
    if grep -q "</html>" "$OUT3"; then
        pass "youtube-cgi empty query renders page with </html>"
    else
        fail "youtube-cgi empty query output lacks </html>:"
        head -c 500 "$OUT3" || true
    fi
else
    fail "youtube-cgi empty query exited non-zero"
    cat "$TESTDIR/cgi-empty.err" || true
fi

# --- Test 4: youtube-gopher with empty env answers menu -------------------
echo "[test] youtube-gopher (empty env) answers Gopher menu"
OUT4="$TESTDIR/gopher-empty.out"
if env -u QUERY_STRING -u SERVER_NAME -u SERVER_PORT -u PATH_INFO \
        -u X_GOPHER_SEARCH -u SEARCHREQUEST \
        "$GOPHER_BIN" >"$OUT4" 2>"$TESTDIR/gopher-empty.err"; then
    if grep -q "7Search" "$OUT4"; then
        pass "youtube-gopher empty env answers menu with 7Search"
    else
        fail "youtube-gopher empty env output lacks 7Search:"
        head -c 500 "$OUT4" || true
    fi
else
    fail "youtube-gopher empty env exited non-zero"
    cat "$TESTDIR/gopher-empty.err" || true
fi

# --- Test 5 (informational): youtube-feed binary is present ----------------
echo "[info] youtube-feed presence: $FEED_BIN"
command -v "$FEED_BIN" >/dev/null 2>&1 || true

# --- summary ---------------------------------------------------------------
echo ""
echo "=== codemadness-frontends test_package summary ==="
echo "PASS: $PASS  FAIL: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
