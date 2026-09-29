#!/bin/sh
# test_wavegain.sh — wavegain 1.3.1 consumer test (real binary, real asserts).
# Pure shell (no python): printf WAV header + urandom payload.
# 1. -h prints usage. 2. synthesize 16-bit mono 8000Hz WAV. 3. -y applies
# gain (file bytes must change). 4. -c reports a gain value.
set -u
BIN="${1:-wavegain}"
WORK="$PWD/wavegain-test"
rm -rf "$WORK"; mkdir -p "$WORK"
cd "$WORK" || exit 1

"$BIN" -h > usage.txt 2>&1 || { echo "FAIL: -h rc=$?"; exit 1; }
grep -q "Usage: wavegain" usage.txt || { echo "FAIL: no usage line"; cat usage.txt; exit 1; }
echo "PASS: usage: $(head -1 usage.txt)"

# 44-byte PCM header: RIFF/8000/8kHz/mono/16-bit + 16000 payload bytes.
# Payload is a QUIET square tone (+256/-256 alternating every 100 samples):
# low level guarantees a large positive gain so -y must rewrite bytes
# (full-scale noise would measure ~0dB and be skipped as no-op).
printf 'RIFF\244\076\000\000WAVEfmt \020\000\000\000\001\000\001\000\100\037\000\000\200\062\000\000\002\000\020\000data\200\062\000\000' > tone.wav
i=0; pat=""; while [ $i -lt 100 ]; do pat="${pat}\000\001"; i=$((i+1)); done
i=0; patn=""; while [ $i -lt 100 ]; do patn="${patn}\377\000"; i=$((i+1)); done
i=0; while [ $i -lt 40 ]; do printf "$pat$patn" >> tone.wav; i=$((i+1)); done
unset pat patn
[ "$(wc -c < tone.wav)" = "16044" ] || { echo "FAIL: bad fixture size"; exit 1; }
cp tone.wav orig.wav
echo "PASS: fixture tone.wav (16044 bytes)"

"$BIN" -y tone.wav > apply.txt 2>&1 || { echo "FAIL: apply rc=$?"; cat apply.txt; exit 1; }
cmp -s tone.wav orig.wav && { echo "FAIL: payload unchanged after -y"; exit 1; }
echo "PASS: -y rewrote payload"

"$BIN" -c tone.wav > calc.txt 2>&1 || { echo "FAIL: calculate rc=$?"; cat calc.txt; exit 1; }
grep -qE "Gain" calc.txt || { echo "FAIL: no gain report"; cat calc.txt; exit 1; }
echo "PASS: calculate: $(grep -m1 Gain calc.txt)"
echo "WAVEGAIN_TEST PASS"
