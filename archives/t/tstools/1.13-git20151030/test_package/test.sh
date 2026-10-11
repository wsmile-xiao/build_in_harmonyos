#!/bin/sh
# Consumer test for the installed tstools binaries.
set -eu

BIN="${TSTOOLS_BIN:?TSTOOLS_BIN is required}"
WORK="${TMPDIR:-/tmp}/tstools-consumer-test.$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

for tool in es2ts tsinfo tsreport stream_type; do
    if [ ! -x "$BIN/$tool" ]; then
        echo "FAIL: missing installed tool $BIN/$tool"
        exit 1
    fi
done
echo "PASS: expected tstools binaries are installed"

python3 - "$WORK/mini.264" <<'PY'
import base64
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_bytes(
    base64.b64decode("AAAAAWdCwB7aAoC3/gUBAQECAAAAAWjOD8gAAAABZYiEAA==")
)
PY

"$BIN/es2ts" "$WORK/mini.264" "$WORK/mini.ts" >"$WORK/es2ts.log" 2>&1
if [ ! -s "$WORK/mini.ts" ]; then
    echo "FAIL: es2ts did not create a transport stream"
    cat "$WORK/es2ts.log"
    exit 1
fi
echo "PASS: es2ts produced a transport stream"

"$BIN/tsinfo" "$WORK/mini.ts" >"$WORK/tsinfo.log" 2>&1
if ! grep -q "Program 1" "$WORK/tsinfo.log"; then
    echo "FAIL: tsinfo did not report the generated program"
    cat "$WORK/tsinfo.log"
    exit 1
fi
echo "PASS: tsinfo parsed the generated transport stream"

"$BIN/stream_type" "$WORK/mini.ts" >"$WORK/stream_type.log" 2>&1 || true
if [ ! -s "$WORK/stream_type.log" ]; then
    echo "FAIL: stream_type produced no output"
    exit 1
fi
echo "PASS: stream_type inspected the generated stream"
echo "PASS: all tstools consumer checks passed"
