#!/bin/sh
# Consumer test for the conversion tools shipped by the libabw package.
#
# Usage: test_libabw_cli.sh <path-to-installed-abw2text>
#
# Upstream ships no AbiWord sample, so the tools are driven on inputs whose
# handling is well defined: a missing file and a plain-text file must both be
# rejected with a non-zero status, and neither may die from a signal.  That
# proves the tools link and resolve their librevenge generators.
set -u

TOOL=${1:-abw2text}
if [ ! -x "$TOOL" ]; then
    echo "not ok - installed abw2text is not executable: $TOOL"
    exit 1
fi
echo "ok 1 - installed abw2text exists and is executable: $TOOL"

WORK=cli_work
rm -rf "$WORK"
mkdir -p "$WORK"
printf 'this is not an abiword document\n' > "$WORK/plain.txt"

status=0

if "$TOOL" "$WORK/does-not-exist.abw" > "$WORK/missing.out" 2> "$WORK/missing.err"; then
    echo "not ok 2 - a missing input file fails"
    status=1
else
    echo "ok 2 - a missing input file fails with a non-zero exit code"
fi

"$TOOL" "$WORK/plain.txt" > "$WORK/plain.out" 2> "$WORK/plain.err"
rc=$?
if [ $rc -eq 0 ]; then
    echo "not ok - plain text was accepted as an AbiWord document"
    status=1
elif [ $rc -ge 128 ]; then
    echo "not ok - plain text processing died from a signal (exit $rc)"
    status=1
else
    echo "ok 3 - plain text is rejected cleanly (exit $rc)"
fi

if [ $status -eq 0 ]; then
    echo "ok 4 - unsupported input is rejected without a crash"
else
    echo "not ok 4 - unsupported input is rejected without a crash"
fi

rm -rf "$WORK"
exit $status
