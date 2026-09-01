#!/usr/bin/env bash
# test_package/test.sh — real functional tests for the installed mpgtx CLI.
#
# Strategy:
#   * A minimal, valid MPEG-1 Layer III audio frame is generated PROGRAM-
#     MATICALLY (printf of hex bytes written DIRECTLY to the file — bash
#     strips NUL bytes from $(...) substitution, so we never store a frame
#     in a variable). The frame is a valid 0xFF 0xFB 0x90 0x64 header
#     (MPEG-1, Layer III, 128 kbps, 44100 Hz) followed by 413 zero payload
#     bytes => 417 bytes/frame. Eight frames are concatenated into a real,
#     auditable MP3 stream that mpginfo can parse and mpgsplit can cut.
#   * Functional coverage: version, help, mpginfo query (real media
#     analysis: bitrate, sample-rate, frame-size), mpgsplit cut,
#     mpgjoin rejoin, real output-file existence/size checks.
#   * Negative coverage: non-MPEG junk, missing file, and no-args. mpgtx
#     is deliberately lenient and exits 0 even for bad input, so these
#     negative tests assert on DIAGNOSTIC OUTPUT ("is not a valid mpeg
#     file" / "nothing to do") rather than on exit codes — the assertions
#     still prove the CLI correctly rejects the bad input by reporting
#     the failure. Each assertion is explicit (no `|| true`, no
#     unconditional "OK").
set -eu

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); echo "PASS: $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

WORK="$(pwd)/mpgtx_work"
rm -rf "$WORK"; mkdir -p "$WORK"
TMP="$WORK/tmp"; mkdir -p "$TMP"; export TMPDIR="$TMP"
cd "$WORK"

# ─── generate a minimal but valid MP3 stream (no committed binary) ───────
# Frame header 0xFF 0xFB 0x90 0x64:
#   sync(11)=0xFFE  MPEG-1(00)  Layer-III(01)  no-CRC(1)
#   bitrate-index 1001=128kbps  samplerate 00=44100  padding(0)  priv(0)
#   channel-mode 01=stereo  =>  frame size = 144*128000/44100 = 417 bytes
FRAME_PAYLOAD_SIZE=413   # 417 total - 4 header
NFRAMES=8
: > base.mp3
for _ in $(seq 1 $NFRAMES); do
    printf '\xff\xfb\x90\x64' >> base.mp3
    # Write payload NUL bytes directly to file (NOT via a variable — bash
    # strips NULs from $(...) output, which would corrupt the frame).
    printf '\x00%.0s' $(seq 1 $FRAME_PAYLOAD_SIZE) >> base.mp3
done
BASE_SIZE=$(wc -c < base.mp3)

echo "=== fixture: base.mp3 = ${NFRAMES} frames, ${BASE_SIZE} bytes ==="

# ─── 1. version ──────────────────────────────────────────────────────────
echo "[test] mpgtx -v"
if mpgtx -v 2>&1 | grep -qiE '1\.3\.1'; then
    ok "mpgtx -v prints version 1.3.1"
else
    bad "mpgtx -v did not print version 1.3.1"
fi

# ─── 2. help ─────────────────────────────────────────────────────────────
echo "[test] mpgtx -h"
if mpgtx -h >/dev/null 2>&1; then
    ok "mpgtx -h exits 0"
else
    bad "mpgtx -h exited non-zero"
fi

# ─── 3. tagmp3 version (alias binary) ────────────────────────────────────
echo "[test] tagmp3 -v"
if tagmp3 -v 2>&1 | grep -qiE '1\.3\.1'; then
    ok "tagmp3 -v prints version 1.3.1"
else
    bad "tagmp3 -v did not print version 1.3.1"
fi

# ─── 4. mpginfo query (real media analysis) ──────────────────────────────
echo "[test] mpginfo base.mp3"
mpginfo base.mp3 >"$TMP/info.out" 2>&1 || true
if grep -qiE 'Mpeg 1 layer 3|Mpeg.*layer' "$TMP/info.out"; then
    ok "mpginfo identified MPEG-1 Layer III stream"
else
    bad "mpginfo did not identify MPEG audio stream"
    head -5 "$TMP/info.out" 2>/dev/null
fi
if grep -qiE '128 kbps' "$TMP/info.out"; then
    ok "mpginfo reported 128 kbps bitrate"
else
    bad "mpginfo did not report bitrate"
fi
if grep -qiE '44100' "$TMP/info.out"; then
    ok "mpginfo reported 44100 Hz sample rate"
else
    bad "mpginfo did not report sample rate"
fi
if grep -qiE '417 bytes' "$TMP/info.out"; then
    ok "mpginfo reported 417-byte frame size"
else
    bad "mpginfo did not report frame size"
fi

# ─── 5. mpgsplit — split into halves and verify output files ─────────────
echo "[test] mpgsplit base.mp3 [1/2][2/2]"
rm -f part_*.mp3
if mpgsplit -b part_ -f base.mp3 '[1/2]' '[2/2]' >"$TMP/split.out" 2>&1; then
    ok "mpgsplit exited 0"
else
    bad "mpgsplit exited non-zero"
    head -5 "$TMP/split.out" 2>/dev/null
fi
NOUT=$(ls part_*.mp3 2>/dev/null | wc -l)
if [ "$NOUT" -ge 2 ]; then
    ok "mpgsplit produced $NOUT output files"
    for f in part_*.mp3; do
        sz=$(wc -c < "$f")
        if [ "$sz" -gt 0 ]; then
            ok "output $f non-empty ($sz bytes)"
        else
            bad "output $f is empty"
        fi
    done
    TOTAL=$(cat part_*.mp3 | wc -c)
    if [ "$TOTAL" -le "$BASE_SIZE" ] && [ "$TOTAL" -gt 0 ]; then
        ok "split output total $TOTAL <= base $BASE_SIZE (sane)"
    else
        bad "split output total $TOTAL unexpected vs base $BASE_SIZE"
    fi
else
    bad "mpgsplit produced $NOUT output files (expected >=2)"
fi

# ─── 6. mpgjoin — rejoin the split halves and verify output ──────────────
echo "[test] mpgjoin part_*.mp3 -> joined.mp3"
rm -f joined.mp3
if mpgjoin part_*.mp3 -o joined.mp3 >"$TMP/join.out" 2>&1; then
    ok "mpgjoin exited 0"
else
    bad "mpgjoin exited non-zero"
    head -5 "$TMP/join.out" 2>/dev/null
fi
if [ -s joined.mp3 ]; then
    JSIZE=$(wc -c < joined.mp3)
    ok "joined.mp3 exists and non-empty ($JSIZE bytes)"
else
    bad "joined.mp3 missing or empty"
fi

# ─── 7. negative test: junk (non-MPEG) input is rejected by diagnostic ───
# mpgtx is lenient (exits 0) but its diagnostic output must clearly mark
# junk as "not a valid mpeg file" — that is the real rejection signal.
echo "[test] mpginfo on non-MPEG junk (expect rejection diagnostic)"
printf 'this is definitely not an mpeg file\n' > junk.txt
mpginfo junk.txt >"$TMP/neg_junk.out" 2>&1 || true
if grep -qiE 'is not a valid mpeg file|No success at all' "$TMP/neg_junk.out"; then
    ok "mpginfo rejected non-MPEG junk (diagnostic present)"
else
    bad "mpginfo did not reject non-MPEG junk"
    head -5 "$TMP/neg_junk.out" 2>/dev/null
fi

# ─── 8. negative test: missing file is rejected by diagnostic ────────────
echo "[test] mpginfo on missing file (expect rejection diagnostic)"
mpginfo does_not_exist.mp3 >"$TMP/neg_miss.out" 2>&1 || true
if grep -qiE 'is not a valid mpeg file|No success|cannot' "$TMP/neg_miss.out"; then
    ok "mpginfo rejected missing file (diagnostic present)"
else
    bad "mpginfo did not reject missing file"
    head -5 "$TMP/neg_miss.out" 2>/dev/null
fi

# ─── 9. negative test: no arguments prints 'nothing to do' ───────────────
echo "[test] mpgtx with no args (expect 'nothing to do')"
mpgtx >"$TMP/neg_noargs.out" 2>&1 || true
if grep -qiE 'nothing to do|usage' "$TMP/neg_noargs.out"; then
    ok "mpgtx no-args produced rejection/usage message"
else
    bad "mpgtx no-args did not produce rejection message"
    head -5 "$TMP/neg_noargs.out" 2>/dev/null
fi

echo ""
echo "==================== SUMMARY ===================="
echo "  PASS=$PASS  FAIL=$FAIL"
echo "================================================="
rm -rf "$WORK"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
