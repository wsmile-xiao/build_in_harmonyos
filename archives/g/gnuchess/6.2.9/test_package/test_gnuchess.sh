#!/bin/sh
# Consumer test for GNU Chess 6.2.9 — asserts real engine behaviour.
set -e
BIN="$1"
if [ -z "$BIN" ]; then
    echo "usage: test_gnuchess.sh <package-bindir>" >&2
    exit 2
fi

# 1-3. the three shipped executables must exist
for tool in gnuchess gnuchessu gnuchessx; do
    [ -e "$BIN/$tool" ] || { echo "FAIL: missing $tool" >&2; exit 1; }
done

# 4. the engine must search and answer a move for a fixed command
#    (native CLI syntax: `depth N` sets the search depth, `go` moves)
OUT=$(printf 'depth 3\ngo\nquit\n' | "$BIN/gnuchess" 2>&1)
echo "$OUT"
echo "$OUT" | grep -q "My move is" \
    || { echo "FAIL: engine produced no move" >&2; exit 1; }

echo "gnuchess 6.2.9 consumer test: OK (3 executables + engine move assertion)"
