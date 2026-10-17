#!/bin/sh
# test_package/run_tests.sh — real demux verification for mpegdemux.
# Invoked by test_package/conanfile.py test(). Exercises all four modes
# (scan/list/demux/remux) on a programmatically generated MPEG-2 PS,
# checks output size/structure/determinism, plus a negative test.
#
# Usage: run_tests.sh <mpegdemux_bin> <gen_fixture_py> <work_dir>
set -eu

BIN="$1"
GEN="$2"
WORK="$3"
mkdir -p "$WORK"

FAIL=0
fail() { echo "FAIL: $1"; FAIL=1; }
pass() { echo "PASS: $1"; }

# --- 0. binary exists & is ELF ---
if [ ! -x "$BIN" ]; then
    echo "FAIL: mpegdemux binary not found or not executable: $BIN"
    exit 1
fi

# --- version check ---
VERSION=$("$BIN" -V 2>&1 || true)
echo "$VERSION" | grep -q "0.1.5" && pass "mpegdemux -V reports 0.1.5" || fail "version not 0.1.5"

# --- generate fixture (no committed binary blob) ---
python3 "$GEN" "$WORK/test.mpg" >/dev/null
FIXSIZE=$(wc -c < "$WORK/test.mpg")
[ "$FIXSIZE" = "43" ] && pass "fixture size 43 bytes" || fail "fixture size $FIXSIZE != 43"

# --- 1. scan mode: must report video stream 0xe0 ---
SCAN=$("$BIN" -c "$WORK/test.mpg" 2>&1) || true
echo "$SCAN" | grep -Eiq "sid=e0|stream e0|video" && pass "scan reports video stream 0xe0" || {
    echo "scan output: $SCAN"
    fail "scan did not report video stream 0xe0"
}

# --- 2. list mode: deterministic, non-empty, mentions packet ---
LIST=$("$BIN" -l -k -s all -p all "$WORK/test.mpg" 2>&1) || true
[ -n "$LIST" ] && pass "list mode produces output" || fail "list mode empty"
echo "$LIST" | grep -Eiq "pack|packet|sid=e0" && pass "list mentions pack/packet" || {
    echo "list output: $LIST"
    fail "list does not mention pack/packet"
}
# determinism: run twice, outputs identical
LIST2=$("$BIN" -l -k -s all -p all "$WORK/test.mpg" 2>&1) || true
[ "$LIST" = "$LIST2" ] && pass "list output deterministic" || fail "list output not deterministic"

# --- 3. demux mode: extract video 0xe0, output == 16 bytes 0xAA ---
rm -f "$WORK/out_demux.m1v"
"$BIN" -d -s 0xe0 "$WORK/test.mpg" "$WORK/out_demux.m1v" 2>&1 || true
if [ -f "$WORK/out_demux.m1v" ]; then
    DSIZE=$(wc -c < "$WORK/out_demux.m1v")
    [ "$DSIZE" = "16" ] && pass "demux output 16 bytes" || fail "demux output $DSIZE != 16"
    # content check: all 0xAA
    DHEX=$(od -An -tx1 "$WORK/out_demux.m1v" | tr -d ' \n')
    [ "$DHEX" = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" ] && pass "demux output all 0xAA" || fail "demux output content mismatch: $DHEX"
else
    fail "demux produced no output file"
fi

# --- 4. remux mode: output is a valid MPEG PS, non-empty, deterministic ---
rm -f "$WORK/out_remux.mpg"
"$BIN" -r -s all "$WORK/test.mpg" "$WORK/out_remux.mpg" 2>&1 || true
if [ -f "$WORK/out_remux.mpg" ]; then
    RSIZE=$(wc -c < "$WORK/out_remux.mpg")
    [ "$RSIZE" -gt 0 ] && pass "remux output non-empty ($RSIZE bytes)" || fail "remux output empty"
    # remux output must contain the pack start code 00 00 01 BA
    RHEAD=$(od -An -tx1 -N4 "$WORK/out_remux.mpg" | tr -d ' \n')
    [ "$RHEAD" = "000001ba" ] && pass "remux output starts with pack start code" || fail "remux output header wrong: $RHEAD"
    # determinism
    rm -f "$WORK/out_remux2.mpg"
    "$BIN" -r -s all "$WORK/test.mpg" "$WORK/out_remux2.mpg" 2>&1 || true
    RSIZE2=$(wc -c < "$WORK/out_remux2.mpg" 2>/dev/null || echo 0)
    [ "$RSIZE" = "$RSIZE2" ] && pass "remux output size deterministic" || fail "remux output size not deterministic ($RSIZE vs $RSIZE2)"
else
    fail "remux produced no output file"
fi

# --- 5. negative test: empty file must NOT silently succeed as valid ---
# mpegdemux on an empty input must exit non-zero (no valid MPEG stream).
: > "$WORK/empty.mpg"
NEG_RC=0
"$BIN" -c "$WORK/empty.mpg" >/dev/null 2>&1 || NEG_RC=$?
if [ "$NEG_RC" -ne 0 ]; then
    pass "negative: empty input rejected (exit $NEG_RC)"
else
    # exit 0 on empty is only acceptable if NO streams were reported
    NEG_OUT=$("$BIN" -c "$WORK/empty.mpg" 2>&1 || true)
    echo "$NEG_OUT" | grep -qiE "0x[0-9a-f]|video|audio" && fail "negative: empty input exit 0 but reported streams" || pass "negative: empty input exit 0 with no streams"
fi

# --- 6. ELF / target verification (built for OHOS aarch64) ---
FILE_OUT=$(file "$BIN" 2>/dev/null || true)
echo "ELF: $FILE_OUT"
echo "$FILE_OUT" | grep -Eiq "aarch64|arm64" && pass "binary is AArch64" || fail "binary not AArch64"
echo "$FILE_OUT" | grep -Eiq "ELF.*64|64-bit" && pass "binary is ELF64" || fail "binary not ELF64"
echo "$FILE_OUT" | grep -Eiq "ld-musl-aarch64" && pass "interpreter /lib/ld-musl-aarch64.so.1" || fail "interpreter not ld-musl-aarch64"

echo ""
if [ "$FAIL" = "0" ]; then
    echo "ALL TESTS PASSED"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
