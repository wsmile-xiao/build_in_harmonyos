#!/usr/bin/env bash
# test_apertium.sh — consumer smoke test for the apertium core engine.
# R34: substantively exercises the tested package by running its real
# binaries (no echo-only stubs). Invoked by test_package/conanfile.py.
# Uses pipefail + explicit assertions so a missing binary (L1e sabotage)
# or an empty/stub binary fails hard instead of passing silently.
#
# Usage: bash test_apertium.sh <bindir> [result_file]
#   3 real assertions:
#     1. `apertium -V` prints the packaged version and exits 0
#     2. `apertium-deshtml` wraps HTML tags in stream markup (kills cat-stubs)
#     3. deshtml|rehtml round-trip restores the original input
# When result_file is given, the PASS summary is tee'd there so the
# conanfile.py test() can read real numbers from disk (self.run() output
# itself is not capturable, so numbers-on-stdout alone would be constants).

set -euo pipefail

BIN_DIR="${1:?usage: test_apertium.sh <bindir> [result_file]}"
RESULT_FILE="${2:-}"
APERTIUM="$BIN_DIR/apertium"
DESHTML="$BIN_DIR/apertium-deshtml"
REHTML="$BIN_DIR/apertium-rehtml"

PASS_COUNT=0

# L1e: moved-away bin/ must fail here, not later with a confusing error.
for b in "$APERTIUM" "$DESHTML" "$REHTML"; do
    if [ ! -x "$b" ]; then
        echo "FAIL: binary not found or not executable: $b" >&2
        exit 1
    fi
done

echo "=== Test 1/3: apertium -V reports 3.9.12 ==="
VERSION_OUT=$(bash "$APERTIUM" -V 2>&1)
echo "$VERSION_OUT"
case "$VERSION_OUT" in
    *3.9.12*)
        echo "PASS: version string contains 3.9.12"
        PASS_COUNT=$((PASS_COUNT + 1))
        ;;
    *)
        echo "FAIL: version output missing 3.9.12: $VERSION_OUT" >&2
        exit 1
        ;;
esac

echo "=== Test 2/3: apertium-deshtml tags HTML markup ==="
INPUT_HTML="<p>Hello World</p>"
DEFORMATTED=$(printf '%s' "$INPUT_HTML" | "$DESHTML" 2>&1)
echo "$DEFORMATTED"
if [ -z "$DEFORMATTED" ]; then
    echo "FAIL: apertium-deshtml produced empty output (stub/empty binary?)" >&2
    exit 1
fi
# A real deformatter keeps the text but wraps tags in stream markup ([...]).
# An identity stub (cat) would echo the input byte-for-byte without brackets.
case "$DEFORMATTED" in
    *Hello*World*\[*)
        echo "PASS: deformatted output keeps text and adds stream markup"
        PASS_COUNT=$((PASS_COUNT + 1))
        ;;
    *)
        echo "FAIL: unexpected deformatter output: $DEFORMATTED" >&2
        exit 1
        ;;
esac

echo "=== Test 3/3: deshtml|rehtml round-trip restores input ==="
ROUNDTRIP=$(printf '%s' "$INPUT_HTML" | "$DESHTML" 2>/dev/null | "$REHTML" 2>&1)
echo "$ROUNDTRIP"
if [ -z "$ROUNDTRIP" ]; then
    echo "FAIL: round-trip produced empty output" >&2
    exit 1
fi
case "$ROUNDTRIP" in
    *"$INPUT_HTML"*)
        echo "PASS: round-trip restored original input"
        PASS_COUNT=$((PASS_COUNT + 1))
        ;;
    *)
        echo "FAIL: round-trip mismatch, expected [$INPUT_HTML], got [$ROUNDTRIP]" >&2
        exit 1
        ;;
esac

echo "PASS_COUNT=$PASS_COUNT/3"
echo "=== All apertium smoke tests passed ==="
if [ -n "$RESULT_FILE" ]; then
    {
        echo "PASS_COUNT=$PASS_COUNT/3"
        echo "PASSES=$PASS_COUNT"
        echo "DISCOVERED=3"
    } > "$RESULT_FILE"
fi
exit 0
