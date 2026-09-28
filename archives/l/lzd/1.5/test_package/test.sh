#!/usr/bin/env sh
# lzd consumer test — decompress the upstream fox.lz fixture and diff
# against its known plaintext (the quick brown fox...).
set -eu

LZD="$1"
FIXTURES="$2"

TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT

"$LZD" < "$FIXTURES/fox.lz" > "$TMPD/fox.txt" 2>/dev/null || {
  echo "FAIL: lzd -d fox.lz"; exit 1; }

if [ -s "$TMPD/fox.txt" ] && grep -q "quick brown fox" "$TMPD/fox.txt" 2>/dev/null; then
  echo "fox-decode: OK"
else
  echo "fox-decode: FAIL (output: $(head -c 60 "$TMPD/fox.txt" 2>/dev/null))"
  exit 1
fi

# empty-member file (em.lz): decompresses to an EMPTY file (upstream check.sh:58-60)
"$LZD" < "$FIXTURES/em.lz" > "$TMPD/em.txt" 2>/dev/null && [ -f "$TMPD/em.txt" ] && [ ! -s "$TMPD/em.txt" ] && \
  echo "em-decode: OK" || { echo "em-decode: FAIL"; exit 1; }

# corrupted input must be rejected (negative control)
printf 'garbage-not-lzip' > "$TMPD/bad.lz"
if "$LZD" < "$TMPD/bad.lz" > /dev/null 2>&1; then
  echo "negative-control: FAIL (accepted garbage)"
  exit 1
else
  echo "negative-control: OK (rejected)"
fi

echo "test_lzd: OK (fox/em decode + negative control)"
