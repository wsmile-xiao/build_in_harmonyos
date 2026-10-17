#!/bin/sh
# jkmeter-0.9.0 packaged-tool smoke test.
#
# jkmeter is an X11+JACK GUI meter: it cannot run to completion headless on
# OHOS/CI, so the pass condition is layered (readings recorded per layer):
#
#   Layer 1 (loading): the binary exists, is executable, and its full runtime
#           shared-library closure resolves — otherwise the dynamic loader
#           dies with exit 127 before main() runs.
#   Layer 2a (entry/-help): `jkmeter -help` prints the "jkmeter-0.9.0"
#           version banner to stderr and exits 1 (upstream help() calls
#           exit(1)) — proves main() started and the clxclient/Xrm paths run.
#   Layer 2b (process): with no arguments and no X server, jkmeter constructs
#           X_display, prints "Can't open display." and exits 1 — proves the
#           process reaches the display check with every dependency linked.
#           exit 127 would mean a loader failure; anything else means the
#           process layer misbehaved.
#
# NOTE: OHOS /system/bin/sh (toybox) lacks command substitution `$(...)`,
# so captures are done through a temp file instead.
#
# Usage: test_jkmeter.sh <path-to-bin-dir>

set -u

BIN_DIR="$1"
ERRFILE="./jkmeter-smoke.err"

if [ ! -x "$BIN_DIR/jkmeter" ]; then
    echo "FAIL: jkmeter not found or not executable in $BIN_DIR" >&2
    exit 1
fi

# Layer 2a: -help must print the version banner (exit code 1 expected upstream,
# but the pipe consumer is grep, so only the banner is asserted here).
if ! "$BIN_DIR/jkmeter" -help 2>&1 | grep -q "jkmeter-0.9.0"; then
    echo "FAIL: jkmeter -help did not print the version banner" >&2
    "$BIN_DIR/jkmeter" -help 2>&1 | head -n 5 >&2
    exit 1
fi

# Layer 2b: no arguments, no X server -> clean "Can't open display." exit 1.
"$BIN_DIR/jkmeter" >/dev/null 2>"$ERRFILE"
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL: jkmeter returned $rc, expected 1 (1 = display check reached;" >&2
    echo "      127 = shared-library load failure)" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi
if ! grep -q "Can't open display" "$ERRFILE"; then
    echo "FAIL: expected 'Can't open display.' on stderr" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi
rm -f "$ERRFILE"

echo "JKMETER_SMOKE_PASS banner=1 nodisplay_exit=1 display_msg=1"
exit 0
