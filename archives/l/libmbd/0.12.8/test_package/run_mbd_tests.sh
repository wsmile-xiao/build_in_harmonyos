#!/bin/sh
# libmbd test_package shell entry (L0c gate + real consumer check).
# Runs the Fortran consumer binary and asserts 3 MBD_TEST_PASS markers.
# Usage: sh run_mbd_tests.sh [path/to/test_mbd]
set -u
BIN="${1:-./test_mbd}"
if [ ! -f "$BIN" ]; then
    echo "MBD_SH_FAIL: binary not found: $BIN" >&2
    exit 1
fi
OUTPUT=$("$BIN" 2>&1)
STATUS=$?
printf "%s\n" "$OUTPUT"
if [ $STATUS -ne 0 ]; then
    echo "MBD_SH_FAIL: test_mbd exit $STATUS" >&2
    exit $STATUS
fi
COUNT=$(printf "%s\n" "$OUTPUT" | grep -c "MBD_TEST_PASS")
if [ "$COUNT" -ne 3 ]; then
    echo "MBD_SH_FAIL: PASS markers ${COUNT}/3" >&2
    exit 1
fi
echo "MBD_SH_ALL_PASS: 3/3 via $BIN"
exit 0
