#!/bin/sh
# test_package/test_mtu.sh - smoke test for the mtu executable.
# Usage: test_mtu.sh <path-to-mtu-binary>
# Invoked by conanfile.py with the packaged binary's full path.
#
# mtu needs a raw ICMP socket plus network for its real modes (-d/-D/-i/-I),
# which a headless package test cannot rely on. The argument-parsing usage
# path (no raw socket) still proves the binary executes: bare `mtu` and an
# unknown option both reach usage() which prints to stderr and exits 3.
# Four deterministic assertions, one RESULT trailer for machine parsing.
set -u

MTU="${1:?usage: test_mtu.sh <mtu binary>}"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "[ok] $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "[fail] $1"
}

if [ ! -x "$MTU" ]; then
    bad "mtu binary not executable: $MTU"
    echo "RESULT: $PASS passed, $FAIL failed"
    exit 1
fi

OUT1="$("$MTU" 2>&1)"
RC1=$?
echo "[test] bare mtu rc=$RC1"
echo "$OUT1" | head -8
if [ "$RC1" -eq 3 ]; then
    ok "bare mtu exits 3 on usage path"
else
    bad "bare mtu exits 3 on usage path (got rc=$RC1)"
fi

OUT2="$("$MTU" -z 2>&1)"
RC2=$?
echo "[test] mtu -z rc=$RC2"
if [ "$RC2" -eq 3 ]; then
    ok "unknown option exits 3 on usage path"
else
    bad "unknown option exits 3 on usage path (got rc=$RC2)"
fi

if [ -n "$OUT1" ]; then
    ok "usage output is non-empty"
else
    bad "usage output is non-empty (got empty output)"
fi

case "$OUT1" in
    *"usage: mtu"*"-d"*)
        ok "usage output documents the flags"
        ;;
    *)
        bad "usage output documents the flags"
        ;;
esac

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
