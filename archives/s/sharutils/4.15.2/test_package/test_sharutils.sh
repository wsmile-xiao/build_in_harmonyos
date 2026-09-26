#!/bin/sh
# Consumer smoke test for sharutils: verify the packaged shar/unshar and
# uuencode/uudecode binaries roundtrip real non-empty payloads.
# Usage: test_sharutils.sh <bindir>
set -u

BINDIR="${1:?usage: test_sharutils.sh <bindir>}"
TMPBASE="${TMPDIR:-${TMP:-${TEMP:-}}}"
[ -n "$TMPBASE" ] || TMPBASE="$(pwd)"
WORK="$TMPBASE/sharutils-test-$PPID"
mkdir -p "$WORK" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

passed=0
failed=0

# Case 1: uuencode -> uudecode roundtrip preserves every byte.
printf 'hello sharutils uu roundtrip\nsecond line: 1234567890\n' > "$WORK/orig.txt"
if [ ! -s "$WORK/orig.txt" ]; then
    echo "FAIL: uu fixture is empty, refusing a vacuous comparison"
    failed=$((failed + 1))
elif ( cd "$WORK" && "$BINDIR/uuencode" orig.txt orig.txt > enc.uue ) \
    && [ -s "$WORK/enc.uue" ] \
    && mkdir -p "$WORK/uudec" \
    && ( cd "$WORK/uudec" && "$BINDIR/uudecode" ../enc.uue ) \
    && cmp -s "$WORK/orig.txt" "$WORK/uudec/orig.txt" \
    && grep -q "hello sharutils uu roundtrip" "$WORK/uudec/orig.txt"; then
    echo "PASS: uuencode/uudecode roundtrip is byte-identical"
    passed=$((passed + 1))
else
    echo "FAIL: uuencode/uudecode roundtrip mismatch"
    failed=$((failed + 1))
fi

# Case 2: shar -> unshar roundtrip preserves every byte.
printf 'hello sharutils shar roundtrip\npayload line: abcdef\n' > "$WORK/payload.txt"
if [ ! -s "$WORK/payload.txt" ]; then
    echo "FAIL: shar fixture is empty, refusing a vacuous comparison"
    failed=$((failed + 1))
elif ( cd "$WORK" && "$BINDIR/shar" payload.txt > pkg.sh ) \
    && [ -s "$WORK/pkg.sh" ] \
    && mkdir -p "$WORK/unpacked" \
    && ( cd "$WORK/unpacked" && "$BINDIR/unshar" ../pkg.sh ) \
    && cmp -s "$WORK/payload.txt" "$WORK/unpacked/payload.txt" \
    && grep -q "hello sharutils shar roundtrip" "$WORK/unpacked/payload.txt"; then
    echo "PASS: shar/unshar roundtrip is byte-identical"
    passed=$((passed + 1))
else
    echo "FAIL: shar/unshar roundtrip mismatch"
    failed=$((failed + 1))
fi

echo "RESULT: passed=$passed failed=$failed"
[ "$failed" -eq 0 ] || exit 1
exit 0
