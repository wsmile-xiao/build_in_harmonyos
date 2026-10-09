#!/bin/sh
# Consumer smoke test for the installed cpulimit binary.
set -eu

CPULIMIT_BIN="${CPULIMIT_BIN:-cpulimit}"

if [ ! -f "$CPULIMIT_BIN" ]; then
    echo "FAIL: cpulimit binary not found at $CPULIMIT_BIN"
    exit 1
fi
echo "PASS: cpulimit binary found"

if [ ! -x "$CPULIMIT_BIN" ]; then
    echo "FAIL: cpulimit binary is not executable"
    exit 1
fi
echo "PASS: cpulimit binary is executable"

# cpulimit prints usage and exits 1 when no target is supplied.
output=$("$CPULIMIT_BIN" --help 2>&1) || true
case "$output" in
    *Usage*|*cpulimit*)
        echo "PASS: cpulimit usage output is available"
        ;;
    *)
        echo "FAIL: unexpected cpulimit output: $output"
        exit 1
        ;;
esac

echo "PASS: all cpulimit consumer checks passed"
