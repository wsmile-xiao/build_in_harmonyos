#!/bin/sh
# Consumer test for the conversion tools shipped by the libwps package.
#
# Usage: test_libwps_cli.sh <path-to-installed-wps2text>
#
# Upstream ships no Microsoft Works sample, so the tools are driven on inputs
# whose handling is well defined: a missing file, a plain-text file, and a
# file carrying only a structurally valid Works v2 header (which the library
# is expected to accept — that same header is a positive case in the C++ test).
set -u

TOOL=${1:-wps2text}
if [ ! -x "$TOOL" ]; then
    echo "not ok 1 - installed wps2text is not executable: $TOOL"
    exit 1
fi
echo "ok 1 - installed wps2text exists and is executable: $TOOL"

WORK=cli_work
rm -rf "$WORK"
mkdir -p "$WORK"
printf 'this is not a microsoft works document\n' > "$WORK/plain.txt"
# First byte 0x02 (< 6) and second byte 0xFE: the Microsoft Works v2 magic
# (WPSHeader::constructHeader), padded past the 0x100-byte length gate of
# WPS4Parser::checkHeader — 2 + 510 = 0x200 bytes in total.
{ printf '\002\376'; head -c 510 /dev/zero; } > "$WORK/header.wps"

status=0

if "$TOOL" "$WORK/does-not-exist.wps" > "$WORK/missing.out" 2> "$WORK/missing.err"; then
    echo "not ok 2 - a missing input file fails"
    status=1
else
    echo "ok 2 - a missing input file fails with a non-zero exit code"
fi

# A plain-text file is not a Works document: the tool must reject it
# with a non-zero status, and must not die from a signal.
"$TOOL" "$WORK/plain.txt" > "$WORK/plain.out" 2> "$WORK/plain.err"
rc=$?
if [ $rc -eq 0 ]; then
    echo "not ok 3 - plain text was accepted as a Works document"
    status=1
elif [ $rc -ge 128 ]; then
    echo "not ok 3 - plain text processing died from a signal (exit $rc)"
    status=1
else
    echo "ok 3 - plain text is rejected cleanly (exit $rc)"
fi

# A structurally valid Works v2 header followed by zero bytes: the detector
# accepts it (the positive case of the C++ test) and the parser then walks an
# all-zero body.  Upstream leaves the exact outcome unspecified; what is
# checked here is that the run stays inside the library's contract — no
# crash, no fatal signal — and the observed outcome is recorded for the log.
"$TOOL" "$WORK/header.wps" > "$WORK/header.out" 2> "$WORK/header.err"
rc=$?
if [ $rc -ge 128 ]; then
    echo "not ok 4 - header-only input died from a signal (exit $rc)"
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
