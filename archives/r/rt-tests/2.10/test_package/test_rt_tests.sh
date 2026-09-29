#!/bin/sh
# Consumer functional test for the installed rt-tests 2.10 binaries.
#
# The measurement tools require SCHED_FIFO, which needs CAP_SYS_NICE and is not
# available to the non-root test user on OHOS, so for those we verify the
# build/version/help surface. hackbench runs without realtime privileges and is
# executed for real.
set -u

D="${RT_BINDIR:?RT_BINDIR must point at the installed bin dir}"
[ -d "$D" ] || { echo "FAIL- missing bindir $D"; exit 1; }

checks=0
fails=0
ck() {
    checks=$((checks + 1))
    if printf '%s\n' "$3" | grep -q -- "$2"; then
        echo "ok  - $1"
    else
        echo "FAIL- $1: expected '$2'"
        fails=$((fails + 1))
    fi
}

# rt-migrate-test prints "rt-migrate-test 2.10"; the rest print "V 2.10".
for b in cyclictest signaltest sigwaittest ptsematest pi_stress pip_stress \
         cyclicdeadline deadline_test queuelat ssdd oslat; do
    out=$("$D/$b" --help 2>&1 || true)
    ck "$b builds and reports V 2.10" "V 2.10" "$out"
done
out=$("$D/rt-migrate-test" --help 2>&1 || true)
ck "rt-migrate-test builds and reports 2.10" "rt-migrate-test 2.10" "$out"

# hackbench runs without RT privileges.
out=$("$D/hackbench" -p -l 3 -g 2 -s 100 2>&1 || true)
ck "hackbench runs a real workload" "Time:" "$out"

# svsematest / ssdd banners (keep the package contents covered).
out=$("$D/svsematest" --help 2>&1 || true)
ck "svsematest builds" "V 2.10" "$out"

echo "RT_TESTS_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
