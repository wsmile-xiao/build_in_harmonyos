#!/usr/bin/env bash
# test_package/test.sh — behavior test for the installed dbeacon executable.
#
# Runs inside the conanrun environment (PATH includes the installed bin/).
# Every check counts as one assertion; the script exits non-zero as soon as one
# check fails.  Note: `dbeacon -V` and `dbeacon -h` both terminate with exit
# status 1 upstream (they print and fall through), so their exit codes are not
# used as the pass/fail criterion — the printed content is.
set -uo pipefail

work_dir="$(pwd)/dbeacon-smoke-$$"
mkdir -p "$work_dir" || exit 1
dump="$work_dir/dump.xml"

pass=0
fail=0
check() {
    # check <description> <file> <fixed string>
    if grep -Fq -- "$3" "$2"; then
        printf 'PASS: %s\n' "$1"
        pass=$((pass + 1))
    else
        printf 'FAIL: %s (expected %s in %s)\n' "$1" "'$3'" "$2"
        fail=$((fail + 1))
    fi
}

# ── 1/3: version banner ─────────────────────────────────────────────────────
printf '[test] dbeacon -V\n'
dbeacon -V >"$work_dir/version.txt" 2>&1
check "version banner identifies the beacon" "$work_dir/version.txt" \
      "dbeacon - a Multicast Beacon"
check "artifact self-reported version string" "$work_dir/version.txt" "0.3.9.2p1"

# ── 2/3: usage output ───────────────────────────────────────────────────────
printf '[test] dbeacon -h\n'
dbeacon -h >"$work_dir/usage.txt" 2>&1
check "usage line" "$work_dir/usage.txt" "Usage: dbeacon [OPTIONS...]"
check "multicast group option is documented" "$work_dir/usage.txt" \
      "-b BEACON_ADDR[/PORT]"

# ── 3/3: real beacon run producing an XML dump ──────────────────────────────
printf '[test] dbeacon IPv4 multicast run -> dump.xml\n'
(
    cd "$work_dir" || exit 1
    exec dbeacon -4 -n OHOSTEST -a ohos@example.com -b 239.192.0.1 -I 1 -d dump.xml
) >"$work_dir/beacon.log" 2>&1 &
beacon_pid=$!

# Poll for the first periodic dump (interval 1s) for at most 20s.
i=0
while [ "$i" -lt 20 ]; do
    if [ -s "$dump" ] && grep -Fq '<beacon name="OHOSTEST"' "$dump"; then
        break
    fi
    sleep 1
    i=$((i + 1))
done

kill "$beacon_pid" 2>/dev/null
wait "$beacon_pid" 2>/dev/null

printf '[test] beacon stdout/stderr:\n'
sed 's/^/        /' "$work_dir/beacon.log"

if [ ! -s "$dump" ]; then
    printf 'FAIL: no non-empty dump.xml was produced by the beacon run\n'
    fail=$((fail + 1))
else
    check "dump.xml carries the self-reported version fingerprint" "$dump" \
          'versioninfo="0.3.9.2p1'
    check "dump.xml announces the local beacon name" "$dump" '<beacon name="OHOSTEST"'
    check "dump.xml carries the administration contact" "$dump" 'contact="ohos@example.com"'
    check "dump.xml reports the joined multicast group" "$dump" '<group addr="239.192.0.1/10000"'
fi

printf 'DBEACON_TEST_SUMMARY passed=%d failed=%d\n' "$pass" "$fail"
if [ "$fail" -ne 0 ]; then
    printf 'RESULT: FAIL\n'
    exit 1
fi
printf 'RESULT: PASS (%d assertions)\n' "$pass"
exit 0
