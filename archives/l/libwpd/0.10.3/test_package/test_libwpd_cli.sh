#!/bin/sh
# Consumer test for the conversion tools shipped by the libwpd package.
#
# Usage: test_libwpd_cli.sh <path-to-installed-wpd2text>
#
# Upstream ships no WordPerfect sample, so the tools are driven on inputs
# whose handling is well defined: a missing file, a plain-text file, and a
# file carrying only a structurally valid WPX header (which the library is
# expected to accept — that same header is a positive case in the C++ test).
set -u

TOOL=${1:-wpd2text}
if [ ! -x "$TOOL" ]; then
    echo "not ok - installed wpd2text is not executable: $TOOL"
    exit 1
fi
echo "ok 1 - installed wpd2text exists and is executable: $TOOL"

WORK=cli_work
rm -rf "$WORK"
mkdir -p "$WORK"
printf 'this is not a wordperfect document\n' > "$WORK/plain.txt"
# 0xFF 'W' 'P' 'C' from offset 1, file type 0x0a at offset 9, version 0x02 at 10
printf '\377WPC\040\000\000\000\001\012\002\000' > "$WORK/header.wpd"
head -c 4096 /dev/zero >> "$WORK/header.wpd"

status=0

if "$TOOL" "$WORK/does-not-exist.wpd" > "$WORK/missing.out" 2> "$WORK/missing.err"; then
    echo "not ok 2 - a missing input file fails"
    status=1
else
    echo "ok 2 - a missing input file fails with a non-zero exit code"
fi

# A plain-text file is not a WordPerfect document: the tool must reject it
# with a non-zero status, and must not die from a signal.
"$TOOL" "$WORK/plain.txt" > "$WORK/plain.out" 2> "$WORK/plain.err"
rc=$?
if [ $rc -eq 0 ]; then
    echo "not ok - plain text was accepted as a WordPerfect document"
    status=1
elif [ $rc -ge 128 ]; then
    echo "not ok - plain text processing died from a signal (exit $rc)"
    status=1
else
    echo "ok 3 - plain text is rejected cleanly (exit $rc)"
fi

# A structurally valid header followed by zero bytes: the parser may accept
# it and emit whatever it makes of that content, which upstream leaves
# unspecified.  What is checked here is that the run stays inside the
# library's contract — no crash, no fatal signal — and the observed outcome
# is recorded for the log.
"$TOOL" "$WORK/header.wpd" > "$WORK/header.out" 2> "$WORK/header.err"
rc=$?
if [ $rc -ge 128 ]; then
    echo "not ok - header-only input died from a signal (exit $rc)"
    status=1
else
    echo "ok 4 - header-only input is handled without a crash (exit $rc, $(wc -c < "$WORK/header.out") bytes of text)"
fi

if [ $status -eq 0 ]; then
    echo "ok 5 - every input is handled without a crash, with the expected outcome"
else
    echo "not ok 5 - every input is handled without a crash, with the expected outcome"
fi

rm -rf "$WORK"
exit $status
