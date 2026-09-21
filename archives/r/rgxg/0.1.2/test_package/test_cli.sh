#!/bin/sh
# Consumer test for the packaged rgxg command line on HarmonyOS PC.
# Every expected expression below is one of the upstream table vectors in
# tests/check_rgxg_{net,number}.c, so the CLI is checked against upstream's
# own answer key rather than against a hand-written guess.
#
# usage: sh test_cli.sh <rgxg package folder>
set -u

PKG="${1:?usage: test_cli.sh <rgxg package folder>}"
BIN="$PKG/bin/rgxg"

total=0
pass=0
fail=0

check() {
    # check <label> <condition-result(0|1)>
    total=$((total + 1))
    if [ "$2" -eq 0 ]; then
        pass=$((pass + 1))
        printf '[PASS] %s\n' "$1"
    else
        fail=$((fail + 1))
        printf '[FAIL] %s\n' "$1"
    fi
}

expect_stdout() {
    # expect_stdout <label> <expected> <args...>
    label="$1"
    want="$2"
    shift 2
    got="$("$BIN" "$@" 2>/dev/null)"
    rc=$?
    total=$((total + 1))
    if [ $rc -eq 0 ] && [ "$got" = "$want" ]; then
        pass=$((pass + 1))
        printf '[PASS] %s\n' "$label"
    else
        fail=$((fail + 1))
        printf '[FAIL] %s (rc=%s)\n       got  %s\n       want %s\n' \
            "$label" "$rc" "$got" "$want"
    fi
}

expect_rc_nonzero() {
    label="$1"
    shift
    "$BIN" "$@" >/dev/null 2>&1
    rc=$?
    total=$((total + 1))
    if [ $rc -ne 0 ]; then
        pass=$((pass + 1))
        printf '[PASS] %s (rc=%s)\n' "$label" "$rc"
    else
        fail=$((fail + 1))
        printf '[FAIL] %s exited 0\n' "$label"
    fi
}

expect_contains() {
    # expect_contains <label> <needle> <args...>
    label="$1"
    needle="$2"
    shift 2
    out="$("$BIN" "$@" 2>&1)"
    rc=$?
    total=$((total + 1))
    case "$out" in
        *"$needle"*)
            [ $rc -eq 0 ] && { pass=$((pass + 1)); printf '[PASS] %s\n' "$label"; return; }
            fail=$((fail + 1)); printf '[FAIL] %s (rc=%s)\n' "$label" "$rc"
            ;;
        *)
            fail=$((fail + 1))
            printf '[FAIL] %s: output has no "%s"\n' "$label" "$needle"
            ;;
    esac
}

if [ ! -x "$BIN" ]; then
    printf '[FAIL] %s is missing or not executable\n' "$BIN"
    printf 'TOTAL=1 PASS=0 FAIL=1\n'
    exit 1
fi

expect_contains "rgxg version reports the upstream release" "rgxg 0.1.2" version
expect_contains "rgxg help lists the cidr command" "cidr" help
expect_contains "rgxg help lists the range command" "range" help
expect_contains "rgxg help lists the escape command" "escape" help
expect_contains "rgxg help lists the alternation command" "alternation" help
expect_contains "rgxg help cidr documents its argument" "CIDR" help cidr

expect_stdout "rgxg cidr 0.0.0.0/24" \
    '0\.0\.0\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])' cidr 0.0.0.0/24
expect_stdout "rgxg cidr 0.0.0.0/32 collapses" '0\.0\.0\.0' cidr 0.0.0.0/32
expect_stdout "rgxg cidr 192.0.2.232/32 is literal" '192\.0\.2\.232' cidr 192.0.2.232/32
expect_stdout "rgxg range 0 31 in base 10" '(3[01]|[12]?[0-9])' range 0 31
expect_stdout "rgxg range -b 2 0 31" '(1[01]{0,4}|0)' range -b 2 0 31
expect_stdout "rgxg range -N -z 0 31 honours both options" '3[01]|[0-2][0-9]' \
    range -N -z 0 31
expect_stdout "rgxg escape quotes every metacharacter" 'a\.b\*c\+d' escape 'a.b*c+d'
expect_stdout "rgxg alternation joins the patterns" '(foo|bar)' alternation foo bar

expect_rc_nonzero "an unknown command fails" definitely-not-a-command
expect_rc_nonzero "no arguments fails"
expect_rc_nonzero "an IPv4 prefix above 32 fails" cidr 10.0.0.0/33

printf 'TOTAL=%s PASS=%s FAIL=%s\n' "$total" "$pass" "$fail"
[ "$fail" -eq 0 ]
