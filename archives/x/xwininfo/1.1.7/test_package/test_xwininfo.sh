#!/bin/sh
# Real HarmonyOS consumer checks for the installed xwininfo binary.
# POSIX sh only: the Conan run environment supplies the platform shell.
# No X server is required; the root-window check validates either a successful
# read-only query or xwininfo's documented connection failure.

XWININFO_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ ! -x "$XWININFO_BIN" ]; then
    echo "FAIL: packaged xwininfo binary is missing or not executable: $XWININFO_BIN"
    exit 1
fi

BIN_DIR=$(dirname "$XWININFO_BIN")
export LD_LIBRARY_PATH="$BIN_DIR:${LD_LIBRARY_PATH:-}"
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

discovered=3
passed=0

echo "[test 1/$discovered] packaged xwininfo --help"
if help_output=$("$XWININFO_BIN" --help 2>&1); then
    help_rc=0
else
    help_rc=$?
fi
printf '%s\n' "$help_output"
if [ "$help_rc" -eq 0 ] && printf '%s\n' "$help_output" | grep -Fq "where options include:"; then
    echo "PASS: help path exits successfully and prints usage"
    passed=$((passed + 1))
else
    echo "FAIL: help path did not return the upstream usage output"
fi

echo "[test 2/$discovered] packaged xwininfo --version"
if version_output=$("$XWININFO_BIN" --version 2>&1); then
    version_rc=0
else
    version_rc=$?
fi
printf '%s\n' "$version_output"
if [ "$version_rc" -eq 0 ] && printf '%s\n' "$version_output" | grep -Fq "xwininfo 1.1.7"; then
    echo "PASS: version path reports xwininfo 1.1.7"
    passed=$((passed + 1))
else
    echo "FAIL: version path did not report xwininfo 1.1.7"
fi

echo "[test 3/$discovered] packaged xwininfo -root with DISPLAY unset"
if root_output=$( ( unset DISPLAY XAUTHORITY; "$XWININFO_BIN" -root ) 2>&1 ); then
    root_rc=0
else
    root_rc=$?
fi
printf '%s\n' "$root_output"
if [ "$root_rc" -eq 0 ] && printf '%s\n' "$root_output" | grep -Fq "Window id:"; then
    echo "PASS: read-only root-window query completed on an available X display"
    passed=$((passed + 1))
elif [ "$root_rc" -eq 1 ] && { printf '%s\n' "$root_output" | grep -Fq "unable to open display" || printf '%s\n' "$root_output" | grep -Fq 'unable to parse display name ""'; }; then
    echo "PASS: no-display environment reports the upstream diagnostic"
    passed=$((passed + 1))
else
    echo "FAIL: root-window query returned an unexpected result (exit $root_rc)"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered consumer checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xwininfo.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered HarmonyOS consumer checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xwininfo.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
