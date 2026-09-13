#!/bin/sh
# test_package/test_bruteforce_luks.sh — bruteforce-luks 1.4.0 smoke test
# Real execution of the packaged binary (application package, no linkable lib):
# assertion 1: `bruteforce-luks -h` prints usage mentioning Usage/LUKS
# assertion 2: no-arg invocation prints the Usage hint.
# No temp files (pipe/variable capture only); upstream -h exits EXIT_FAILURE(1)
# by design (src/bruteforce-luks.c usage() + exit(EXIT_FAILURE)), so exit
# codes are neutralized with `|| true` and only output content is asserted.

set -eu

if [ "$#" -lt 1 ]; then
    echo "FAIL: usage: test_bruteforce_luks.sh <bruteforce-luks-binary>"
    exit 1
fi

BIN="$1"
if [ ! -f "$BIN" ]; then
    echo "FAIL: bruteforce-luks binary not found: $BIN"
    exit 1
fi

OUT1=$("$BIN" -h 2>&1 || true)
if [ -z "$OUT1" ]; then
    echo "FAIL: -h produced empty output (expected usage text)"
    exit 1
fi
case "$OUT1" in
    *Usage*LUKS*|*LUKS*Usage*)
        echo "assertion 1 PASSED: -h shows usage for LUKS volume"
        ;;
    *)
        echo "FAIL: -h output missing Usage/LUKS keywords"
        echo "$OUT1" | head -c 500
        echo ""
        exit 1
        ;;
esac

OUT2=$("$BIN" 2>&1 || true)
if [ -z "$OUT2" ]; then
    echo "FAIL: no-arg invocation produced empty output"
    exit 1
fi
case "$OUT2" in
    *Usage*)
        echo "assertion 2 PASSED: no-arg invocation shows usage"
        ;;
    *)
        echo "FAIL: no-arg output missing Usage keyword"
        echo "$OUT2" | head -c 500
        echo ""
        exit 1
        ;;
esac

echo "PASS: bruteforce-luks smoke test verified (2/2 assertions)"
