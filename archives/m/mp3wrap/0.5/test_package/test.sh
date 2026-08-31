#!/bin/sh
# test_package/test.sh — functional test for mp3wrap 0.5
# Runs in conanrun env (PATH includes installed bin/)
# R25: shell scripts must start with `set -euo pipefail`.
# /bin/sh on this OHOS image (/system/bin/sh) supports pipefail; verified
# at authoring time. The conanfile invokes `/bin/sh test.sh`.
# R34: genuinely exercises the tested package's binary — not just --help.
set -euo pipefail

TMPDIR_BASE="${TMPDIR:-/data/storage/el2/base/cache}"
WORKDIR="$(mktemp -d -p "$TMPDIR_BASE" mp3wrap-test.XXXXXX)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "=== mp3wrap 0.5 functional test suite ==="
echo ""

# ---------------------------------------------------------------------------
# Fixture: programmatic generation of minimal, legal MP3 frames
# ---------------------------------------------------------------------------
# An MPEG1 Layer 3 frame at 32 kbps, 44100 Hz, single channel (mono)
# has a frame size of 104 bytes (see ISO/IEC 11172-3 frame size table).
# We generate the 4-byte frame header + 100 zero bytes (silent padding).
# Frame header: 0xFF 0xFB 0x90 0x64
#   0xFFFB = sync word (11 bits) + MPEG1 (2 bits) + Layer 3 (2 bits) + no CRC
#   0x90   = 32 kbps bitrate (index 8 << 4) + 44100 Hz (index 0 << 2) + no pad
#   0x64   = mono (channel mode 11) + no extension + no emphasis + no original
#
# This is a synthetic fixture — NOT copied from any copyrighted audio file.
# Generated programmatically by this test script; no binary .mp3 committed.
# ---------------------------------------------------------------------------

gen_mp3_frame() {
    # $1 = output file, $2 = number of frames
    _out="$1"
    _frames="$2"
    _i=0
    # Clear file
    : > "$_out"
    while [ "$_i" -lt "$_frames" ]; do
        # 4-byte MP3 frame header: FF FB 90 64
        printf '\xff\xfb\x90\x64' >> "$_out"
        # 100 zero bytes (silent padding data)
        _j=0
        while [ "$_j" -lt 100 ]; do
            printf '\x00' >> "$_out"
            _j=$((_j + 1))
        done
        _i=$((_i + 1))
    done
}

# Generate two small MP3 input fixtures (each: 5 frames x 104 bytes = 520 bytes)
gen_mp3_frame "$WORKDIR/input1.mp3" 5
gen_mp3_frame "$WORKDIR/input2.mp3" 5

SIZE1=$(wc -c < "$WORKDIR/input1.mp3")
SIZE2=$(wc -c < "$WORKDIR/input2.mp3")
echo "[1/9] Generated fixture input1.mp3 ($SIZE1 bytes)"
echo "[2/9] Generated fixture input2.mp3 ($SIZE2 bytes)"

# ---------------------------------------------------------------------------
# Test 1: mp3wrap version string
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 1: mp3wrap version banner ---"
BANNER=$(mp3wrap 2>&1 </dev/null || true)
echo "$BANNER" | head -1
echo "$BANNER" | grep -q "Mp3Wrap Version 0.5" || {
    echo "FAIL: version banner does not contain 'Mp3Wrap Version 0.5'"
    exit 1
}
echo "OK: version banner correct"

# ---------------------------------------------------------------------------
# Test 2: merge two MP3 files -> output file created
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 2: merge two MP3 fixtures ---"
cd "$WORKDIR"
mp3wrap merged.mp3 input1.mp3 input2.mp3 2>&1
EXPECTED_OUTPUT="merged_MP3WRAP.mp3"
if [ ! -f "$EXPECTED_OUTPUT" ]; then
    echo "FAIL: output file $EXPECTED_OUTPUT was not created"
    exit 1
fi
echo "OK: output file $EXPECTED_OUTPUT created"

# ---------------------------------------------------------------------------
# Test 3: output file is non-empty
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 3: output file non-empty ---"
OUT_SIZE=$(wc -c < "$EXPECTED_OUTPUT")
if [ "$OUT_SIZE" -le 0 ]; then
    echo "FAIL: output file is empty"
    exit 1
fi
echo "OK: output file is $OUT_SIZE bytes"

# ---------------------------------------------------------------------------
# Test 4: output file contains WRAP index marker
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 4: WRAP index marker present ---"
# The WRAP tag appears after the ID3v2 tag (460 bytes per mp3wrap.h ID3LEN).
# Search the file for the literal "WRAP" string using strings or od.
# Use od -A x -t a (printable chars) which is more portable than -t x1z.
if od -A x -t a "$EXPECTED_OUTPUT" 2>/dev/null | grep -q "W R A P"; then
    echo "OK: WRAP index marker found (via od -t a)"
elif od -A x -t x1 "$EXPECTED_OUTPUT" 2>/dev/null | grep -q "57 52 41 50"; then
    echo "OK: WRAP index marker found (via od -t x1)"
else
    # Try strings as a last resort
    if strings "$EXPECTED_OUTPUT" 2>/dev/null | grep -q "WRAP"; then
        echo "OK: WRAP index marker found (via strings)"
    else
        echo "FAIL: WRAP index marker not found in output"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Test 5: output contains ID3v2 header (ID3 at offset 0)
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 5: ID3v2 header at offset 0 ---"
# Read first 3 bytes and check for "ID3" (0x49 0x44 0x33).
# Primary path: od -A n -t x1 dumps hex ("49 44 33"); strip whitespace.
# Fallback path: od -A n -t a dumps printable chars ("   I   D   3").
#   NOTE: toybox `od` rejects the bare `-a` form ("Unknown option 'a'");
#   the portable equivalent is `-t a`. Strip whitespace -> "ID3".
FIRST3=$(dd if="$EXPECTED_OUTPUT" bs=1 count=3 2>/dev/null | od -A n -t x1 | tr -d ' \n')
if [ "$FIRST3" != "494433" ]; then
    # Fallback: use od -t a (printable char dump); -a is not supported by toybox.
    FIRST3A=$(dd if="$EXPECTED_OUTPUT" bs=1 count=3 2>/dev/null | od -A n -t a | tr -d ' \n')
    if [ "$FIRST3A" != "ID3" ]; then
        echo "FAIL: output does not start with 'ID3' (got 0x$FIRST3 / '$FIRST3A')"
        exit 1
    fi
fi
echo "OK: ID3v2 header present (0x$FIRST3)"

# ---------------------------------------------------------------------------
# Test 6: output size = ID3LEN(460) + index + inputs + overhead
# Output must be larger than sum of inputs (wrap overhead: ID3v2 + WRAP index)
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 6: output larger than sum of inputs (wrap overhead) ---"
INPUT_SUM=$((SIZE1 + SIZE2))
if [ "$OUT_SIZE" -le "$INPUT_SUM" ]; then
    echo "FAIL: output ($OUT_SIZE bytes) should exceed input sum ($INPUT_SUM bytes) due to wrap overhead"
    exit 1
fi
echo "OK: output $OUT_SIZE > input sum $INPUT_SUM (overhead = $((OUT_SIZE - INPUT_SUM)) bytes)"

# ---------------------------------------------------------------------------
# Test 7: list wrapped files with mp3wrap -l
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 7: list wrapped files (mp3wrap -l) ---"
LISTOUT=$(mp3wrap -l "$EXPECTED_OUTPUT" 2>&1 || true)
echo "$LISTOUT"
echo "$LISTOUT" | grep -q "input1.mp3" || {
    echo "FAIL: -l output does not list input1.mp3"
    exit 1
}
echo "$LISTOUT" | grep -q "input2.mp3" || {
    echo "FAIL: -l output does not list input2.mp3"
    exit 1
}
echo "OK: -l lists both input files"

# ---------------------------------------------------------------------------
# Test 8 (negative): nonexistent input file should fail
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 8 (negative): nonexistent input file ---"
# mp3wrap requires OUTPUTFILE + >=2 MP3 inputs. With only 2 args it prints
# the usage help (the insufficient-args path, covered by Test 9) before ever
# touching files. To exercise the real nonexistent-input path we pass
# OUTPUTFILE + 2 inputs where the first input does not exist; mp3wrap then
# attempts to open it and reports "<name>: No such file or directory".
# Upstream contract (verified on the packaged 0.5 binary): exit code 255,
# stderr contains "No such file or directory".
#
# Real assertion: capture output to an audit file, assert nonzero exit AND
# the expected error text. No `|| true`, no unconditional PASS.
set +e
mp3wrap neg.mp3 nonexistent.mp3 input2.mp3 >"$WORKDIR/neg_missing.out" 2>&1
RC_NEG=$?
set -e
if [ "$RC_NEG" -eq 0 ]; then
    echo "FAIL: mp3wrap unexpectedly succeeded (rc=0) on nonexistent input" >&2
    cat "$WORKDIR/neg_missing.out" >&2
    exit 1
fi
if ! grep -q "No such file or directory" "$WORKDIR/neg_missing.out"; then
    echo "FAIL: mp3wrap did not report 'No such file or directory' (rc=$RC_NEG)" >&2
    cat "$WORKDIR/neg_missing.out" >&2
    exit 1
fi
echo "OK: nonexistent input rejected (rc=$RC_NEG, error text present)"

# ---------------------------------------------------------------------------
# Test 9 (negative): too few arguments should show help, not crash
# ---------------------------------------------------------------------------
echo ""
echo "--- Test 9 (negative): insufficient arguments ---"
# Upstream contract (verified on the packaged 0.5 binary): when given only
# OUTPUTFILE (one positional arg) mp3wrap prints the full help including a
# USAGE section and exits with code 255. We assert BOTH the nonzero exit AND
# the presence of the upstream help text ("USAGE"); a crash or a silent
# nonzero exit would fail this test. No `|| true`, no unconditional PASS.
set +e
mp3wrap onlyone.mp3 >"$WORKDIR/neg_toofew.out" 2>&1 </dev/null
RC_TOOFEW=$?
set -e
if [ "$RC_TOOFEW" -eq 0 ]; then
    echo "FAIL: mp3wrap unexpectedly succeeded (rc=0) with insufficient args" >&2
    cat "$WORKDIR/neg_toofew.out" >&2
    exit 1
fi
if ! grep -q -i "USAGE" "$WORKDIR/neg_toofew.out"; then
    echo "FAIL: mp3wrap produced no usage/help text (rc=$RC_TOOFEW)" >&2
    cat "$WORKDIR/neg_toofew.out" >&2
    exit 1
fi
echo "OK: insufficient arguments handled (rc=$RC_TOOFEW, usage text present)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== ALL TESTS PASSED ==="
echo "Summary: 9 checks (2 fixture gen + 1 version + 4 functional + 2 negative)"
exit 0
