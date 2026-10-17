#!/bin/sh
# R34: real smoke tests for colortest 20110624 — exercises the packaged
# artifacts (5 scripts) with presence, executable bit, shebang, syntax
# check and real color-table output.
#
# Security-mode note: this script intentionally uses only `set -u`
# (not `set -euo pipefail`): it is a test collector that accumulates all
# assertion failures into $FAIL and reports them in one pass.  `set -e`
# would abort on the first failed assertion and hide the remaining ones.
# Each assertion is guarded by an explicit if/FAIL=1 check instead.
#
# NOTE: 8colors.sh and 16colors.sh are infinite-loop animation scripts
# (while true ... sleep 1, designed to exit via Ctrl+C), so their output
# is sampled with `timeout 3` + head instead of waiting for exit.

set -u

BIN_DIR="${1:?usage: test_colortest.sh <package bin dir>}"

FAIL=0

# 1. all 5 scripts present and executable
for f in colortest 256colors2.pl 8colors.sh 16colors.sh colortable16.sh; do
    if [ ! -x "$BIN_DIR/$f" ]; then
        echo "FAIL: $f missing or not executable in $BIN_DIR"
        FAIL=1
    fi
done

# 2. shebang sanity
EXPECT_PERL="$(head -1 "$BIN_DIR/colortest")"
case "$EXPECT_PERL" in
    *env*perl*) ;;
    *) echo "FAIL: unexpected colortest shebang: $EXPECT_PERL"; FAIL=1 ;;
esac
EXPECT_PERL2="$(head -1 "$BIN_DIR/256colors2.pl")"
case "$EXPECT_PERL2" in
    *env*perl*) ;;
    *) echo "FAIL: unexpected 256colors2.pl shebang: $EXPECT_PERL2"; FAIL=1 ;;
esac
EXPECT_BASH="$(head -1 "$BIN_DIR/colortable16.sh")"
case "$EXPECT_BASH" in
    *env*bash*) ;;
    *) echo "FAIL: unexpected colortable16.sh shebang: $EXPECT_BASH"; FAIL=1 ;;
esac

# 3. syntax checks (perl -c / sh -n / bash -n)
if ! perl -c "$BIN_DIR/colortest" >/dev/null 2>&1; then
    echo "FAIL: perl -c colortest"
    FAIL=1
fi
if ! perl -c "$BIN_DIR/256colors2.pl" >/dev/null 2>&1; then
    echo "FAIL: perl -c 256colors2.pl"
    FAIL=1
fi
if ! sh -n "$BIN_DIR/8colors.sh"; then
    echo "FAIL: sh -n 8colors.sh"
    FAIL=1
fi
if ! sh -n "$BIN_DIR/16colors.sh"; then
    echo "FAIL: sh -n 16colors.sh"
    FAIL=1
fi
if ! bash -n "$BIN_DIR/colortable16.sh"; then
    echo "FAIL: bash -n colortable16.sh"
    FAIL=1
fi

# 4. real output checks
# colortest (finite perl script): full run must show the test chart
OUT="$(perl "$BIN_DIR/colortest" 2>&1)"
if ! printf '%s' "$OUT" | grep -q "256Color Test Chart"; then
    echo "FAIL: colortest output lacks 256Color Test Chart"
    FAIL=1
fi
# 8colors.sh / 16colors.sh (infinite-loop animation): sample 3s of output
OUT="$(timeout 3 sh "$BIN_DIR/8colors.sh" 2>&1 || true)"
if ! printf '%s' "$OUT" | grep -q "normal"; then
    echo "FAIL: 8colors.sh output lacks 'normal' rows"
    FAIL=1
fi
OUT="$(timeout 3 sh "$BIN_DIR/16colors.sh" 2>&1 || true)"
if ! printf '%s' "$OUT" | grep -q "BLK"; then
    echo "FAIL: 16colors.sh output lacks color rows"
    FAIL=1
fi
# colortable16.sh (finite bash script): full run must show the table
OUT="$(bash "$BIN_DIR/colortable16.sh" 2>&1)"
if ! printf '%s' "$OUT" | grep -q "Background"; then
    echo "FAIL: colortable16.sh output lacks Background section"
    FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
    echo "colortest smoke test: OK"
fi
exit "$FAIL"
