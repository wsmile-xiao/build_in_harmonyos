#!/bin/sh
# Consumer test for the toybox multicall binary: every assertion runs the
# packaged 0.8.9 through a real applet and compares exact output.

TOYBOX="$1"
if [ -z "$TOYBOX" ] || [ ! -x "$TOYBOX" ]; then
    echo "SMOKE_FAIL: no executable toybox at '$TOYBOX'"
    exit 1
fi

PASS=0
FAIL=0

check() {
    name="$1"
    expected="$2"
    actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1))
        echo "ok   - $name"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL - $name: expected [$expected] got [$actual]"
    fi
}

check_rc() {
    name="$1"
    expected="$2"
    actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1))
        echo "ok   - $name"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL - $name: expected rc=$expected got rc=$actual"
    fi
}

check "basename path" "bash" "$("$TOYBOX" basename /usr/local/bin/bash)"
check "seq range" "1
2
3" "$("$TOYBOX" seq 1 3)"
check "sort numeric order" "9
10" "$(printf '10\n9\n' | "$TOYBOX" sort -n)"
check "sha256sum of abc" \
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" \
    "$(printf 'abc' | "$TOYBOX" sha256sum | "$TOYBOX" cut -d' ' -f1)"
check "wc line count" "3" "$(printf 'a\nb\nc\n' | "$TOYBOX" wc -l)"
check "cut field" "b" "$(printf 'a:b:c' | "$TOYBOX" cut -d: -f2)"
check "sed first match" "baa" "$(printf 'aaa' | "$TOYBOX" sed 's/a/b/')"
check "sort order" "1
2
3" "$(printf '3\n1\n2\n' | "$TOYBOX" sort)"
check "wc word count" "3" "$(printf 'a b c' | "$TOYBOX" wc -w)"
check "head lines" "1
2" "$(printf '1\n2\n3\n' | "$TOYBOX" head -n 2)"

"$TOYBOX" basename >/dev/null 2>&1
check_rc "basename without operand fails" "1" "$?"

# The multicall entry point must refuse an applet it was not built with.
"$TOYBOX" definitely-not-an-applet >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    PASS=$((PASS + 1))
    echo "ok   - unknown applet fails (rc=$rc)"
else
    FAIL=$((FAIL + 1))
    echo "FAIL - unknown applet returned 0"
fi

echo "SMOKE pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ]
