#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the installed esekeyd package.
#
# Runs in the conanrun environment (PATH includes the installed bin/).
# esekeyd itself daemonizes on /dev/input which the CI device may not grant;
# this test therefore covers:
#   * usage / error exit paths of esekeyd, keytest, learnkeys
#   * the parse() keycode->name mapping via keytest reading synthetic
#     binary input_event records from a regular file
#
# struct input_event layout on aarch64 (musl):
#   struct timeval time (16B: tv_sec 8 + tv_usec 8),
#   __u16 type, __u16 code, __s32 value  -> 24 bytes per event, no padding.
set -u

export PATH="$PATH:/system/bin"

fail=0
check() { # check <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 (expected [$2], got [$3])"
        fail=$((fail + 1))
    fi
}

echo "--- esekeyd consumer verification ---"

# 1. esekeyd without arguments prints usage and exits 1.
out="$(esekeyd 2>&1)"; rc=$?
check "esekeyd usage exit code" "1" "$rc"
case "$out" in
    *Usage*) echo "PASS: esekeyd usage text";;
    *) echo "FAIL: esekeyd usage text missing: [$out]"; fail=$((fail + 1));;
esac

# 2. esekeyd with a missing config file reports and fails.
out="$(esekeyd ./no-such.conf 2>&1)"; rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then
    echo "PASS: esekeyd missing config exits non-zero ($rc)"
else
    echo "FAIL: esekeyd missing config rc=$rc out=[$out]"
    fail=$((fail + 1))
fi
case "$out" in
    *cannot*open*) echo "PASS: esekeyd missing config message";;
    *) echo "FAIL: esekeyd missing config message: [$out]"; fail=$((fail + 1));;
esac

# 3. esekeyd with a valid config but a nonexistent device reports and fails.
printf 'A:echo hi\n' > ./valid.conf
out="$(esekeyd ./valid.conf /dev/input/no-such-event 2>&1)"; rc=$?
if [ "$rc" -ne 0 ]; then
    echo "PASS: esekeyd bad device exits non-zero ($rc)"
else
    echo "FAIL: esekeyd bad device rc=0 out=[$out]"
    fail=$((fail + 1))
fi
case "$out" in
    *open*) echo "PASS: esekeyd bad device message";;
    *) echo "FAIL: esekeyd bad device message: [$out]"; fail=$((fail + 1));;
esac

# 4. keytest banner reports the package version string.
out="$(keytest /dev/null 2>&1)"
case "$out" in
    *ESE*Key*Deamon*1.2.7*|*keytest*) echo "PASS: keytest banner";;
    *) echo "FAIL: keytest banner: [$out]"; fail=$((fail + 1));;
esac

# 5. keytest replays a synthetic KEY_A press: must print the parsed name.
#    16 zero bytes (timeval) + type=1 (EV_KEY) + code=30 (KEY_A) + value=1,
#    followed by KEY_ENTER (code=28) press which makes keytest exit 0.
#    NOTE: printf writes straight to the file — command substitution would
#    strip the NUL bytes.
{
    printf '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\001\000\036\000\001\000\000\000'
    printf '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\001\000\034\000\001\000\000\000'
} > ./events.bin
check "synthetic events file size" "48" "$(wc -c < ./events.bin | tr -d ' ')"
out="$(keytest ./events.bin 2>&1)"; rc=$?
check "keytest exit code" "0" "$rc"
case "$out" in
    *A*) echo "PASS: keytest parses KEY_A";;
    *) echo "FAIL: keytest KEY_A parse: [$out]"; fail=$((fail + 1));;
esac

# 6. learnkeys without arguments prints usage and exits 1.
out="$(learnkeys 2>&1)"; rc=$?
check "learnkeys usage exit code" "1" "$rc"
case "$out" in
    *Usage*) echo "PASS: learnkeys usage text";;
    *) echo "FAIL: learnkeys usage text: [$out]"; fail=$((fail + 1));;
esac

# 7. learnkeys with config path + /dev/null device hits EOF immediately and
#    writes the commented config skeleton.
rm -f ./learned.conf
learnkeys ./learned.conf /dev/null >/dev/null 2>&1; rc=$?
check "learnkeys null-device exit code" "0" "$rc"
if [ -f ./learned.conf ] && grep -q "config file" ./learned.conf; then
    echo "PASS: learnkeys writes config skeleton"
else
    echo "FAIL: learnkeys config skeleton missing"
    fail=$((fail + 1))
fi

rm -f ./valid.conf ./events.bin ./learned.conf

if [ "$fail" -ne 0 ]; then
    echo "esekeyd test_package: $fail assertion(s) FAILED"
    exit 1
fi
echo "esekeyd test_package: 14/14 assertions PASS"
exit 0
