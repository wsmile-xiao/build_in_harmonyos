#!/usr/bin/env bash
# test_package/test.sh — nInvaders binary CLI smoke test
# nInvaders has no --version switch. Its documented CLI contract is:
#   - unknown option (e.g. -help) -> prints version + usage to stderr, exit 1
# So we run the real binary, assert the version/usage output, and accept the
# upstream exit code 1 which is the normal response for a help-style call.
set -u

BIN="$1"
out=""
rc=0

out="$("$BIN" -help 2>&1)"
rc=$?

echo "$out"
echo "$out" | grep -q "nInvaders" || { echo "[fail] version banner missing"; exit 1; }
echo "$out" | grep -q "Usage: nInvaders" || { echo "[fail] usage line missing"; exit 1; }

# Upstream exits with 1 on unknown/help-style options; that IS the passing
# contract for this game binary (no interactive tty run is attempted in CI).
if [ "$rc" -eq 1 ]; then
    echo "[ok] nInvaders CLI smoke test passed (help path, rc=$rc)"
    exit 0
fi

echo "[fail] unexpected exit code $rc (expected 1 for -help)"
exit 1