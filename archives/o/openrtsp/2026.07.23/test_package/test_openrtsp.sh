#!/bin/sh
# test_openrtsp.sh — consumer smoke test for openRTSP (live555).
#
# live555 has no upstream automated test suite (0/0 official cases). This
# script is the consumer-level smoke test: it runs the packaged openRTSP
# binary with no arguments (which prints a "Usage:" banner and exits 1)
# and asserts:
#   - the process is not terminated by a signal (no crash),
#   - the exit code is the expected usage exit (non-zero, not a signal),
#   - stdout contains the "Usage:" banner.
#
# Invocation: test_openrtsp.sh <openRTSP binary path>
# Exit 0 = PASS, non-zero = FAIL.
set -u

BIN="${1:-}"
if [ -z "$BIN" ]; then
    echo "test_openrtsp: FAIL — missing openRTSP binary path argument" >&2
    exit 2
fi
if [ ! -x "$BIN" ]; then
    echo "test_openrtsp: FAIL — openRTSP binary not found or not executable: $BIN" >&2
    exit 2
fi

# Capture stdout+stderr together. openRTSP with no args prints Usage and
# exits 1; a signal death is reported by the shell as 128 + signum.
OUTPUT=$(export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"; "$BIN" 2>&1)
RC=$?
if [ "$RC" -ge 128 ]; then
    echo "test_openrtsp: FAIL — openRTSP died with signal (rc=$RC, signum=$((RC-128)))" >&2
    printf '%s\n' "$OUTPUT" >&2
    exit 1
fi
if [ "$RC" -eq 0 ]; then
    echo "test_openrtsp: FAIL — openRTSP exited 0 with no args (unexpected success)" >&2
    printf '%s\n' "$OUTPUT" >&2
    exit 1
fi
# Expected usage exit code is 1. Any other non-signal, non-zero code is flagged
# but not fatal — openRTSP's exit-on-usage may vary across builds.
if [ "$RC" -ne 1 ]; then
    echo "test_openrtsp: WARN — openRTSP exited with unexpected code $RC (expected 1)" >&2
fi
case "$OUTPUT" in
    *"Usage:"*)
        echo "test_openrtsp: PASS — rc=$RC, 'Usage:' banner present"
        exit 0
        ;;
    *)
        echo "test_openrtsp: FAIL — output missing 'Usage:' banner (rc=$RC)" >&2
        printf '%s\n' "$OUTPUT" >&2
        exit 1
        ;;
esac
