#!/bin/sh
# Consumer startup/load validation for wily.
#
# wily calls xtbinit() before it parses its own options.  There is no
# non-GUI --version or --help path.  This script executes the packaged binary
# with an intentionally invalid DISPLAY and requires the Xt/Xlib connection
# failure to prove that dynamic loading and startup were reached.
#
# Usage: test_wily.sh <absolute-path-to-wily> [colon-separated-LD_PRELOAD]

WILY_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$WILY_BIN" ]; then
    echo "FAIL: wily binary path not provided"
    exit 1
fi

if [ ! -x "$WILY_BIN" ]; then
    echo "FAIL: $WILY_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$WILY_BIN")
LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
LD_PRELOAD="${LD_PRELOAD_EXTRA}"
DEFAULT_DISPLAY=":65535"

export LD_LIBRARY_PATH
export LD_PRELOAD

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$WILY_BIN" 2>&1 || true
fi

discovered=3
passed=0

echo "[test 1/$discovered] packaged binary exists and is executable"
if [ -x "$WILY_BIN" ]; then
    echo "PASS: $WILY_BIN"
    passed=$((passed + 1))
else
    echo "FAIL: $WILY_BIN is not executable"
fi

TEST_HOME="${TMPDIR:-/tmp}/wily-test-$$"
mkdir -p "$TEST_HOME" 2>/dev/null || TEST_HOME="${TMPDIR:-/}"

echo "[test 2/$discovered] launch wily against DISPLAY=$DEFAULT_DISPLAY"
startup_output=$(cd / && HOME="$TEST_HOME" DISPLAY="$DEFAULT_DISPLAY" "$WILY_BIN" 2>&1)
startup_rc=$?
echo "$startup_output"
echo "[rc] $startup_rc"

if [ "$startup_rc" -eq 0 ]; then
    echo "FAIL: wily unexpectedly exited successfully without a usable display"
else
    echo "PASS: wily reached runtime startup and returned nonzero without a display"
    passed=$((passed + 1))
fi

echo "[test 3/$discovered] expected X server connection failure"
if printf '%s\n' "$startup_output" | grep -E "Can't open display|unable to open display" >/dev/null 2>&1; then
    echo "PASS: Xt/Xlib reported the expected missing display"
    passed=$((passed + 1))
else
    echo "FAIL: expected X connection diagnostic not found"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_wily.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_wily.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
