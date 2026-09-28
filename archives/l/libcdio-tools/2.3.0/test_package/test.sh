#!/bin/sh
set -eu

BINDIR=${1:?usage: test.sh BINDIR FIXTURES}
FIXTURES=${2:?usage: test.sh BINDIR FIXTURES}
WORK="$PWD/.libcdio-tools-test"
EXPECTED_VERSION=2.3.0
ASSERTIONS=0

rm -rf "$WORK"
mkdir -p "$WORK"
export LC_ALL=C
export TZ=UTC

fail() {
    echo "CHECK=FAIL $*" >&2
    exit 1
}

pass() {
    ASSERTIONS=$((ASSERTIONS + 1))
    echo "CHECK=PASS $*"
}

PKG_ROOT=$(dirname -- "$BINDIR")
LIB_ARTIFACTS=$(find "$PKG_ROOT" -type f \( -name '*.a' -o -name '*.so' -o -name '*.so.*' \) -print)
if [ -n "$LIB_ARTIFACTS" ]; then
    echo "$LIB_ARTIFACTS" >&2
    fail "package-scope: library artifacts were packaged"
fi
pass "package-scope: tools-only package"

for TOOL in cd-drive cd-info cd-read iso-info iso-read mmc-tool; do
    [ -x "$BINDIR/$TOOL" ] || fail "$TOOL: installed executable is missing"
    if OUTPUT=$("$BINDIR/$TOOL" --version 2>&1); then
        STATUS=0
    else
        STATUS=$?
    fi
    if [ "$STATUS" -ne 0 ] && [ "$STATUS" -ne 100 ]; then
        fail "$TOOL --version exited with unexpected status $STATUS"
    fi
    if ! printf '%s\n' "$OUTPUT" | grep -F "$TOOL version $EXPECTED_VERSION" >/dev/null; then
        printf '%s\n' "$OUTPUT" >&2
        fail "$TOOL --version did not report version $EXPECTED_VERSION"
    fi
    pass "$TOOL: installed --version output"
 done

OUTPUT=$("$BINDIR/cd-drive" --quiet 2>&1) || fail "cd-drive driver enumeration exited nonzero"
if ! printf '%s\n' "$OUTPUT" | grep -F "Drivers available..." >/dev/null; then
    printf '%s\n' "$OUTPUT" >&2
    fail "cd-drive did not report its compiled driver list"
fi
pass "cd-drive: compiled driver enumeration"

"$BINDIR/cd-info" --no-header --no-device-info \
    --cue-file "$FIXTURES/isofs-m1.cue" --no-tracks --quiet \
    > "$WORK/cd-info.out" 2>&1 || fail "cd-info cue image invocation failed"
if ! diff -u "$FIXTURES/check_opts0.right" "$WORK/cd-info.out" > "$WORK/cd-info.diff"; then
    cat "$WORK/cd-info.diff" >&2
    fail "cd-info output differs from the upstream 2.3.0 fixture"
fi
pass "cd-info: cue image analysis output"

"$BINDIR/cd-read" --no-header --input "$FIXTURES/isofs-m1.cue" \
    --mode m1f1 --start 26 --number 2 \
    > "$WORK/cd-read.out" 2>&1 || fail "cd-read cue image invocation failed"
if ! diff -u "$FIXTURES/isofs-m1-read.right" "$WORK/cd-read.out" > "$WORK/cd-read.diff"; then
    cat "$WORK/cd-read.diff" >&2
    fail "cd-read output differs from the upstream 2.3.0 fixture"
fi
pass "cd-read: mode1 sector read output"

"$BINDIR/iso-info" --no-header --quiet --iso9660 "$FIXTURES/copying.iso" \
    > "$WORK/iso-info.out" 2>&1 || fail "iso-info invocation failed"
if ! diff -u "$FIXTURES/copying.right" "$WORK/iso-info.out" > "$WORK/iso-info.diff"; then
    cat "$WORK/iso-info.diff" >&2
    fail "iso-info output differs from the upstream 2.3.0 fixture"
fi
pass "iso-info: ISO-9660 directory listing"

"$BINDIR/iso-read" --no-header --ignore --image "$FIXTURES/copying.iso" \
    --extract copying --output-file "$WORK/copying.out" \
    > "$WORK/iso-read.log" 2>&1 || fail "iso-read extraction failed"
if ! cmp -s "$FIXTURES/copying.gpl" "$WORK/copying.out"; then
    fail "iso-read extracted bytes do not match the upstream fixture"
fi
pass "iso-read: extracted file byte comparison"

echo "TEST_PACKAGE_RESULT=PASS assertions=$ASSERTIONS tools=6 behaviors=5"
