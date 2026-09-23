#!/bin/sh
# Consumer test for GNU dominion 2.8.2 — asserts real tool behaviour.
#
# dominion's getopt front end rejects unknown options via usageerr() and
# exits 1 (dominion.c:143-144) — a deterministic, data-independent path.
set -e
BIN="$1"
if [ -z "$BIN" ]; then
    echo "usage: test_dominion.sh <package-bindir>" >&2
    exit 2
fi

# 1-5. all five shipped tools must exist and be executable
for tool in dominion dom_make dom_add dom_update dom_print; do
    [ -x "$BIN/$tool" ] || { echo "FAIL: missing $tool" >&2; exit 1; }
done

# 6. an unknown option must be rejected (usage + exit 1)
if "$BIN/dominion" --bogus-flag-x >/dev/null 2>&1; then
    echo "FAIL: dominion accepted an unknown option" >&2
    exit 1
fi

echo "dominion 2.8.2 consumer test: OK (5 tools present + invalid-option rejection)"
