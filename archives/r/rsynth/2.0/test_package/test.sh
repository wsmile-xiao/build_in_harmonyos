#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for rsynth `say` tool
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] say --help"
say --help >/dev/null 2>&1
echo "✅ say --help OK"

# Synthesize "hello world" to a Sun/NeXT .au file and validate the header.
OUT="${TMPDIR:-${HOME}/tmp}/rsynth-test-hello.au"
rm -f "$OUT"
echo "[test] say -o $OUT \"hello world\""
say -o "$OUT" "hello world" >/dev/null 2>&1 || {
    echo "❌ say failed to produce audio output"
    exit 1
}
if [ ! -s "$OUT" ]; then
    echo "❌ output file is empty/missing"
    exit 1
fi
# Sun/NeXT .au header starts with the ".snd" magic (0x2e 0x73 0x6e 0x64).
MAGIC="$(od -A n -t x1 -N 4 "$OUT" | tr -d ' ')"
if [ "$MAGIC" != "2e736e64" ]; then
    echo "❌ output file is not a valid .au audio (magic=$MAGIC)"
    exit 1
fi
echo "✅ synthesized .au file valid ($(wc -c < "$OUT") bytes)"

# Synthesize raw 16-bit linear output.
RAW="${TMPDIR:-${HOME}/tmp}/rsynth-test-num.raw"
rm -f "$RAW"
say -l "$RAW" "numbers 12345" >/dev/null 2>&1 || {
    echo "❌ say -l failed to produce raw linear output"
    exit 1
}
[ -s "$RAW" ] || { echo "❌ raw output file is empty/missing"; exit 1; }
echo "✅ raw 16-bit output valid ($(wc -c < "$RAW") bytes)"

echo "[test] rsynth say smoke test: PASS"
