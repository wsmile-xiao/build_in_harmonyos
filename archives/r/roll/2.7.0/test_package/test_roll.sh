#!/bin/sh
# Consumer-side functional tests for the packaged roll CLI (R34/R51).
#
# 21 assertions, every expectation measured on HarmonyOS PC (aarch64, OHOS SDK
# clang, patched 2.7.0 build) — see ../notes.md (验证结果) and the PR description.
# POSIX sh only: runs under toybox sh (device) and GNU sh (CI worker).
#
# Deliberately not `set -e` (code_style §7 安全模式, same as archives/l/looktxt):
# several assertions evaluate commands that are expected to fail (their exit
# status is the observation) and `grep -c` returns 1 on a zero match; errexit
# would abort the suite instead of recording the result. `set -u` is kept;
# nok() counts failures and the script exits non-zero when FAIL > 0.
set -u

PASS=0
FAIL=0
ok()  { PASS=$((PASS+1)); printf '[PASS] %s\n' "$1"; }
nok() { FAIL=$((FAIL+1)); printf '[FAIL] %s\n' "$1"; }

if ! command -v roll >/dev/null 2>&1; then
    printf '[FAIL] 01 packaged roll is not on PATH\n'
    exit 1
fi
printf '[PASS] 01 packaged roll is on PATH\n'
PASS=$((PASS+1))

# 02 --version prints the package version and exits 0.
out=$(roll --version 2>&1); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "roll 2.7.0" ]; then
    ok "02 --version exits 0 and prints 'roll 2.7.0'"
else
    nok "02 --version exits 0 and prints 'roll 2.7.0' (rc=$rc out='$out')"
fi

# 03 --help exits 0 and advertises the deterministic --test switch.
out=$(roll --help 2>&1); rc=$?
if [ "$rc" = "0" ] && printf '%s' "$out" | grep -q -- '--test'; then
    ok "03 --help exits 0 and documents --test"
else
    nok "03 --help exits 0 and documents --test (rc=$rc)"
fi

# 04 single die: --test forces every die to 3.
out=$(roll --test 1d6); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "3" ]; then
    ok "04 '1d6' rolls a single 3 in --test mode"
else
    nok "04 '1d6' rolls a single 3 in --test mode (rc=$rc out='$out')"
fi

# 05 keep-highest / keep-lowest operators: four 3s, keep three -> 9.
a=$(roll --test 4d6h3); b=$(roll --test 4d6l3); c=$(roll --test 4d6HX); d=$(roll --test 4d6LX)
if [ "$a|$b|$c|$d" = "9|9|9|9" ]; then
    ok "05 4d6h3 / 4d6l3 / 4d6HX / 4d6LX all keep three 3s = 9"
else
    nok "05 keep operators (h3=$a l3=$b HX=$c LX=$d)"
fi

# 06 d% percentile dice: tens 3, units 3 -> 33.
out=$(roll --test 1d%); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "33" ]; then
    ok "06 '1d%' percentile die = 33 (two d10: tens 3, units 3)"
else
    nok "06 '1d%' percentile die = 33 (rc=$rc out='$out')"
fi

# 07 Fudge die: roll(3)-2 = +1.
out=$(roll --test 1DF); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "1" ]; then
    ok "07 '1DF' Fudge die = +1"
else
    nok "07 '1DF' Fudge die = +1 (rc=$rc out='$out')"
fi

# 08 arithmetic operators on rolls: +, -, *, / (ceiling) and the x10 shorthand.
a=$(roll --test '1d6 + 1'); b=$(roll --test 1d10-1); c=$(roll --test 1d%*2)
d=$(roll --test 2D6/2); e=$(roll --test 1d6x10)
if [ "$a|$b|$c|$d|$e" = "4|2|66|3|30" ]; then
    ok "08 1d6+1=4, 1d10-1=2, 1d%*2=66, 2D6/2=3, 1d6x10=30"
else
    nok "08 arithmetic (a=$a b=$b c=$c d=$d e=$e)"
fi

# 09 zero-sided dice are legal and yield 0 (upstream dices.test case 42d0).
out=$(roll --test 42d0); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "0" ]; then
    ok "09 '42d0' zero-sided dice = 0"
else
    nok "09 '42d0' zero-sided dice = 0 (rc=$rc out='$out')"
fi

# 10 -s prints the series sum after the expression value.
out=$(roll --test -s 2d6); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "$(printf '6\nsum: 6')" ]; then
    ok "10 '-s 2d6' prints '6' then 'sum: 6'"
else
    nok "10 '-s 2d6' prints '6' then 'sum: 6' (rc=$rc out='$out')"
fi

# 11 repetition group N{expr} evaluates N times.
out=$(roll --test 3{1d6}); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "$(printf '3\n3\n3')" ]; then
    ok "11 '3{1d6}' rolls the group three times"
else
    nok "11 '3{1d6}' rolls the group three times (rc=$rc out='$out')"
fi

# 12 -s over a repetition group prints the running and final sums.
out=$(roll --test -s 3{1d6}); rc=$?
if [ "$rc" = "0" ] && printf '%s\n' "$out" | grep -qx 'sum: 9'; then
    ok "12 '-s 3{1d6}' reaches the final 'sum: 9'"
else
    nok "12 '-s 3{1d6}' reaches the final 'sum: 9' (rc=$rc out='$out')"
fi

# 13 -v traces the individual die before the result.
out=$(roll --test -v 1d6); rc=$?
if [ "$rc" = "0" ] && printf '%s\n' "$out" | grep -qx 'd6 -> 3' \
    && printf '%s\n' "$out" | tail -1 | grep -qx '3'; then
    ok "13 '-v 1d6' prints the 'd6 -> 3' trace and the result 3"
else
    nok "13 '-v 1d6' prints the 'd6 -> 3' trace and the result 3 (rc=$rc out='$out')"
fi

# 14 without --test the RNG path is used and a d6 stays within 1..6.
out=$(roll 1d6); rc=$?
case "$rc:$out" in
    0:1|0:2|0:3|0:4|0:5|0:6) ok "14 '1d6' random roll is an integer in 1..6" ;;
    *) nok "14 '1d6' random roll is an integer in 1..6 (rc=$rc out='$out')" ;;
esac

# 15 -p clamps the series sum to 0 while the expression value is still printed.
out=$(roll --test -s -p 1d6-10); rc=$?
if [ "$rc" = "0" ] && [ "$out" = "$(printf -- '-7\nsum: 0')" ]; then
    ok "15 '-s -p 1d6-10' prints -7 and clamps 'sum: 0'"
else
    nok "15 '-s -p 1d6-10' prints -7 and clamps 'sum: 0' (rc=$rc out='$out')"
fi

# 16 impossible filter: 1d6 can never exceed 6.
out=$(roll --test '1d6>7' 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q 'Impossible dice filter'; then
    ok "16 impossible filter '1d6>7' is rejected (rc=1)"
else
    nok "16 impossible filter '1d6>7' is rejected (rc=$rc out='$out')"
fi

# 17 division by zero is rejected before any roll.
out=$(roll --test 1d6/0 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q 'Division by zero'; then
    ok "17 division by zero '1d6/0' is rejected (rc=1)"
else
    nok "17 division by zero '1d6/0' is rejected (rc=$rc out='$out')"
fi

# 18 integer overflow in multiplication is detected.
out=$(roll --test 2000000000*2 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q 'Overflow'; then
    ok "18 overflow '2000000000*2' is detected (rc=1)"
else
    nok "18 overflow '2000000000*2' is detected (rc=$rc out='$out')"
fi

# 19 keeping more dice than were rolled is rejected.
out=$(roll --test 3d6h5 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q 'kept dices must be lower'; then
    ok "19 '3d6h5' (keep more than rolled) is rejected (rc=1)"
else
    nok "19 '3d6h5' (keep more than rolled) is rejected (rc=$rc out='$out')"
fi

# 20 no expression is an error.
out=$(roll 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q 'No expression provided'; then
    ok "20 missing expression is rejected (rc=1)"
else
    nok "20 missing expression is rejected (rc=$rc out='$out')"
fi

# 21 unknown symbols are rejected by the scanner.
out=$(roll --test '1d6?' 2>&1); rc=$?
if [ "$rc" = "1" ] && printf '%s' "$out" | grep -q "unknown symbol '?'"; then
    ok "21 unknown symbol is rejected by the scanner (rc=1)"
else
    nok "21 unknown symbol is rejected by the scanner (rc=$rc out='$out')"
fi

printf 'roll test_package: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" = "0" ] || exit 1
exit 0
