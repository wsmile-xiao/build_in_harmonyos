#!/bin/sh
# Behavioural assertion on the delivered program: its usage text must advertise
# the -U/-W socket overrides (the only runtime knobs this package offers, which
# is why no daemon restart is needed to redirect it).
BIN="$1"
if [ ! -x "$BIN" ]; then
  echo "SMOKE_FAIL: no executable at $BIN"
  exit 1
fi
OUT=$(mktemp 2>/dev/null || echo ./utmps-usage.txt)
"$BIN" -h >"$OUT" 2>&1
rc=$?
echo "info - utmps-write -h rc=$rc"
if grep -q 'utmpd-socket' "$OUT" && grep -q 'wtmpd-socket' "$OUT"; then
  echo "ok   - usage advertises the -U/-W socket overrides"
else
  echo "FAIL - usage text lacks the socket override options"
  sed -n '1,5p' "$OUT"
  rm -f "$OUT"
  exit 1
fi
rm -f "$OUT"
echo "SMOKE_CLI pass=1 fail=0"
