#!/bin/sh
# test_package/test.sh — smoke test for catdoc executables
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binaries.
set -eu

echo "[test] catdoc -V (version)"
catdoc -V | grep -q "Catdoc Version"
echo "OK: catdoc -V returns version string"

echo "[test] catdoc (runs without crashing)"
set +e
USAGE=$(catdoc 2>&1)
RC=$?
set -e
# catdoc with no args: either prints Usage (charsets found) or an error
# about missing charset. Either outcome confirms the binary runs.
echo "$USAGE" | head -1
# Fail on missing binary (126/127) or death by signal (>=128, e.g. SIGSEGV)
if [ "$RC" -ge 126 ]; then
    echo "FAIL: catdoc did not run properly (exit $RC)" >&2
    exit 1
fi
echo "OK: catdoc binary runs (exit $RC)"

echo "[test] xls2csv -V (version)"
xls2csv -V | grep -q "Catdoc Version"
echo "OK: xls2csv -V returns version string"

echo "[test] catppt -V (version)"
catppt -V | grep -q "Catdoc Version"
echo "OK: catppt -V returns version string"

echo "[test] catdoc -l (charset listing)"
set +e
CHARSETS=$(catdoc -l 2>&1)
CHARSET_RC=$?
set -e
echo "$CHARSETS" | head -3
# Fail on missing binary (126/127) or death by signal (>=128, e.g. SIGSEGV)
if [ "$CHARSET_RC" -ge 126 ]; then
    echo "FAIL: catdoc -l did not run properly (exit $CHARSET_RC)" >&2
    exit 1
fi
echo "OK: catdoc -l ran (exit $CHARSET_RC)"

echo ""
echo "PASS: all catdoc smoke tests passed"
