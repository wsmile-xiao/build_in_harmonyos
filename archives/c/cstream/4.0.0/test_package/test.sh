#!/bin/sh
# test.sh — cstream consumer checks (cases 2-3; case 1 is `cstream -V`).
# Usage: sh test.sh /path/to/cstream
set -eu
CSTREAM="$1"
# HMOS /tmp is read-only (E002): prefer HMBS-injected TMPDIR, fall back to
# $HOME/tmp, never hardcode /tmp.
TMPD="${TMPDIR:-${HOME}/tmp}/cstream-test-$$"
mkdir -p "$TMPD"

# Case 2: generated-bytes pipe, limit 1k, sink to stdout, verify size.
"$CSTREAM" -i- -n 1k -o "$TMPD/pipe.out"
sz=$(wc -c < "$TMPD/pipe.out" | tr -d " \t")
if [ "$sz" != "1024" ]; then
  echo "pipe test: expected 1024 bytes, got $sz" >&2
  exit 1
fi
echo "pipe test ok: 1024 bytes"

# Case 3: file round-trip, input file preserved byte-for-byte.
printf 'hello cstream harmonyos\n%.0s' 1 2 3 4 5 > "$TMPD/in.txt"
"$CSTREAM" -i "$TMPD/in.txt" -o "$TMPD/out.txt"
cmp "$TMPD/in.txt" "$TMPD/out.txt"
echo "file round-trip ok"

rm -rf "$TMPD"
echo "ALL TESTS PASSED (2/2 in test.sh)"
