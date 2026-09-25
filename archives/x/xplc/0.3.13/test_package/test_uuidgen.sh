#!/bin/sh
# Consumer check for the packaged xplc CLI tools (uuidgen / uuidcdef).
#
# Usage: test_uuidgen.sh <path-to-uuidgen>
# Fails loudly on any shape violation; prints one line per assertion so the
# count is machine-readable in the build log.
set -eu

BIN="$1"
[ -n "$BIN" ] || { echo "usage: $0 <uuidgen>" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: uuidgen is not executable: $BIN" >&2; exit 1; }

fail=0
ok=0

# 1. uuidgen prints exactly one canonical 36-char UUID.
out=$("$BIN")
len=$(printf %s "$out" | wc -c | tr -d ' ')
if [ "$len" = "36" ]; then ok=$((ok + 1)); else
  echo "FAIL: uuidgen printed $len bytes, expected 36: [$out]"; fail=$((fail + 1))
fi

# 2. Shape is 8-4-4-4-12 lowercase hex.
if printf %s "$out" | grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
  ok=$((ok + 1))
else
  echo "FAIL: uuidgen output is not a canonical UUID: [$out]"; fail=$((fail + 1))
fi

# 3. Two runs differ (randomness actually wired up, not a constant).
out2=$("$BIN")
if [ "$out" != "$out2" ]; then ok=$((ok + 1)); else
  echo "FAIL: uuidgen returned the same value twice: [$out]"; fail=$((fail + 1))
fi

# 4. The uuidcdef symlink installed next to it selects the C-def sink.
DEF="${BIN%uuidgen}uuidcdef"
if [ -x "$DEF" ]; then
  defout=$("$DEF" 2>/dev/null || true)
  case "$defout" in
    \{*\}) ok=$((ok + 1)) ;;
    *) echo "FAIL: uuidcdef did not emit a braced C definition: [$defout]"
       fail=$((fail + 1)) ;;
  esac
else
  echo "FAIL: uuidcdef symlink missing at $DEF"; fail=$((fail + 1))
fi

echo "xplc tool assertions: $ok passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
