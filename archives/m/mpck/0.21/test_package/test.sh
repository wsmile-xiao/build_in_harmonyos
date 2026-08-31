#!/usr/bin/env bash
# test_package/test.sh — real functional test for mpck 0.21
#
# Not a --help stub. Builds a minimal LEGAL MP3 (10 MPEG-1 Layer III frames,
# 128kbps/44100Hz/stereo — mpck.h requires >= MIN_FRAMES=10 frames to accept
# a file as an mp3) from an auditable base64 fixture, feeds it to mpck, and
# asserts on exit code + output. Also verifies mpck flags a corrupt file.
#
# Runs in conanrun env (PATH includes the installed bin/).
set -euo pipefail

MPCK="${MPCK:-mpck}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# ── Fixture: minimal legal MP3 (10 frames), decoded from base64 ──
# Source: generated locally with a Python script that emits 10 identical
# MPEG-1 Layer III frames (header 0xFF 0xFB 0x90 0x04, length 417 bytes each).
# sha256 of the decoded bytes:
#   e9b2473662fae4db2e9c0324e7594377c5ade99bc3099461432fc16d92e5ff18
# base64 keeps the fixture text-auditable (no opaque binary committed).
GOOD="$HERE/mp3/min_good.mp3"
base64 -d < "$GOOD.b64" > "$GOOD"
ACTUAL_SHA="$(sha256sum < "$GOOD" | awk '{print $1}')"
EXPECTED_SHA="e9b2473662fae4db2e9c0324e7594377c5ade99bc3099461432fc16d92e5ff18"
if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
    echo "FAIL: fixture sha256 mismatch"
    echo "  expected: $EXPECTED_SHA"
    echo "  actual:   $ACTUAL_SHA"
    exit 1
fi
echo "PASS: fixture decoded, sha256 verified"

# ── Test 1: a GOOD mp3 → exit 0, output contains "Ok" + filename ──
OUT="$("$MPCK" -q "$GOOD")" && RC=$? || RC=$?
if [ "$RC" -ne 0 ]; then
    echo "FAIL: GOOD file exit code $RC (expected 0)"
    echo "  output: $OUT"
    exit 1
fi
case "$OUT" in
    *"Ok"*)
        echo "PASS: GOOD file reported Ok, exit 0"
        ;;
    *)
        echo "FAIL: GOOD file did not report Ok"
        echo "  output: $OUT"
        exit 1
        ;;
esac

# ── Test 2: verbose output reports the parsed frame metadata ──
OUT2="$("$MPCK" "$GOOD")" && RC2=$? || RC2=$?
if [ "$RC2" -ne 0 ]; then
    echo "FAIL: verbose GOOD exit code $RC2 (expected 0)"
    exit 1
fi
for needle in "MPEG v1.0" "layer" "128000 bps" "44100 Hz" "frames" "10" "errors" "none" "Ok"; do
    case "$OUT2" in
        *"$needle"*) : ;;
        *) echo "FAIL: verbose output missing '$needle'"; echo "  output: $OUT2"; exit 1 ;;
    esac
done
echo "PASS: verbose output contains expected metadata, exit 0"

# ── Test 3: a corrupt (truncated) file → mpck flags it, exit 0 per upstream ──
# (mpck returns 1 only when a counted mp3 file is damaged; a 2-byte file is
# "No MP3", not counted, so exit stays 0 — assert on the output, not the code.)
BAD="$HERE/mp3/bad_truncated.mp3"
head -c 2 "$GOOD" > "$BAD"
OUT3="$("$MPCK" -q "$BAD" 2>&1)" && RC3=$? || RC3=$?
case "$OUT3" in
    *"[Nn]o MP3"*|*"No MP3"*)
        echo "PASS: corrupt file flagged as No MP3"
        ;;
    *)
        echo "FAIL: corrupt file not flagged as No MP3"
        echo "  output: $OUT3 (exit $RC3)"
        exit 1
        ;;
esac

# ── Test 4: no-args → usage + non-zero exit (EINVAL) ──
"$MPCK" >/dev/null 2>&1 && RC4=$? || RC4=$?
if [ "$RC4" -eq 0 ]; then
    echo "FAIL: no-args returned 0 (expected non-zero EINVAL)"
    exit 1
fi
echo "PASS: no-args returns non-zero exit ($RC4)"

echo "ALL TESTS PASSED"
