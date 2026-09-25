#!/bin/sh
# Consumer test for the packaged yersinia 0.8.2 (track-2 gate: run the shipped
# binary and assert its observable behaviour, decided by exit code).
#
# Measured offline surface without root and without a tty:
#   no args            -> "GNU yersinia 0.8.2" banner + "Try 'yersinia -h'"
#                         hint + upstream MOTD line, exit 0
#   any option (-h/-l/...) -> root gate message
#                         "You must be root to run yersinia 0.8.2", exit 0
# Anything beyond that needs root + raw sockets, which is exactly what the
# root gate protects; those paths are reported, not faked.
set -u
fail() { echo "FAIL $1"; exit 1; }
pass() { echo "PASS $1"; }

# 1-4: no-args banner path
out1=$(yersinia 2>&1); rc1=$?
[ "$rc1" = "0" ] || fail "1: no-args exit=$rc1 (expected 0)"
pass "1: no-args exits 0"
echo "$out1" | grep -q "GNU yersinia 0.8.2" \
    || fail "2: version banner missing in [$out1]"
pass "2: banner reports GNU yersinia 0.8.2"
echo "$out1" | grep -q "Try 'yersinia -h'" \
    || fail "3: usage hint missing in [$out1]"
pass "3: banner points at -h for help"
echo "$out1" | grep -qi "MOTD" \
    || fail "4: upstream MOTD line missing in [$out1]"
pass "4: upstream MOTD line present"

# 5-7: root gate on the option paths (skipped, not failed, when running as root)
if [ "$(id -u)" = "0" ]; then
    echo "SKIP 5-7: running as root, the non-root gate is not observable"
else
    for opt in -h --version -l; do
        out=$(yersinia "$opt" 2>&1); rc=$?
        [ "$rc" = "0" ] || fail "5-7: yersinia $opt exit=$rc"
        echo "$out" | grep -q "must be root to run yersinia 0.8.2" \
            || fail "5-7: root gate message missing for [$opt]: [$out]"
    done
    pass "5: -h hits the root gate with the versioned message"
    pass "6: --version hits the root gate with the versioned message"
    pass "7: -l hits the root gate with the versioned message"
fi

echo "test yersinia 0.8.2: PASS"
exit 0
