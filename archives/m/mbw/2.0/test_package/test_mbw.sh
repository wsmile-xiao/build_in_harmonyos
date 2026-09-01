#!/bin/sh
# Runs the packaged mbw benchmark on a tiny array and verifies it produced a
# bandwidth measurement. Usage: test_mbw.sh <path-to-mbw> [-n 1 -a 8]
BINARY="$1"
shift
if [ ! -x "$BINARY" ]; then
    echo "FAIL: mbw binary not executable: $BINARY" >&2
    exit 1
fi
OUTPUT="$("$BINARY" "$@" 2>&1)"
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
    echo "FAIL: mbw exited $STATUS" >&2
    echo "$OUTPUT" >&2
    exit 1
fi
case "$OUTPUT" in
    *"Copy:"*) ;;
    *)
        echo "FAIL: mbw produced no bandwidth result" >&2
        echo "$OUTPUT" >&2
        exit 1
        ;;
esac
echo "ok: mbw benchmark ran and produced a bandwidth result"
exit 0
