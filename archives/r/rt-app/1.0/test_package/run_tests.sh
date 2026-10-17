#!/bin/sh
# run_tests.sh - rt-app 1.0 consumer test driver.
#
# POSIX sh on purpose: the OHOS worker has no /bin/bash (only /bin/sh), and the
# CI runner invokes this script through `sh`.
#
# usage: sh run_tests.sh <rt-app> <cc> <work-dir> <test-src-dir>
#
# Every case below executes the *packaged* rt-app executable (or a test program
# compiled by the same toolchain that built it) and asserts on real output and
# real files it produces. Cases named OHOS_* are the HarmonyOS-specific ones.
#
# Emits a machine-readable HMBS_TEST_PACKAGE_RESULT marker for the CI reporter.

set -u

RTAPP="${1:?packaged rt-app executable required}"
CC="${2:?C compiler required}"
WORK_DIR="${3:?work folder required}"
SRC_DIR="${4:?test source folder required}"

# The work folder is disposable: fresh at entry, removed on every exit path so
# no build product is ever left behind in the recipe tree.
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM

PASSED=0
FAILED=0
SKIPPED=0
OHOS_CASES=0
OHOS_PASSED=0

emit() {
    # $1=executed $2=passed $3=discovered $4=passedCount $5=ohosCases $6=ohosPassed $7=reason
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\": $1, \"passed\": $2, \"discovered\": $3, \"passedCount\": $4, \"ohosCases\": $5, \"ohosPassed\": $6, \"command\": \"sh run_tests.sh\", \"reason\": \"$7\"}"
}

record() {
    # $1=STATUS $2=case-id $3=description
    case "$1" in
        PASS) PASSED=$((PASSED + 1)) ;;
        FAIL) FAILED=$((FAILED + 1)) ;;
        SKIP) SKIPPED=$((SKIPPED + 1)) ;;
    esac
    case "$2" in
        OHOS_*)
            OHOS_CASES=$((OHOS_CASES + 1))
            [ "$1" = "PASS" ] && OHOS_PASSED=$((OHOS_PASSED + 1))
            ;;
    esac
    echo "$1 $2 $3"
}

echo "=== rt-app 1.0 test_package ==="
echo "rt-app : $RTAPP"
echo "cc     : $CC"

if [ ! -x "$RTAPP" ]; then
    echo "ERROR: packaged rt-app executable not found or not executable: $RTAPP"
    emit false false 0 0 0 0 "rt_app_missing"
    exit 1
fi

echo
echo "--- CLI behaviour of the packaged binary ---"

# Case 1: invoked with no argument, rt-app must print its usage and exit 0.
OUT="$WORK_DIR/usage.out"
"$RTAPP" > "$OUT" 2>"$WORK_DIR/usage.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "rt-app <taskset.json>" "$OUT"; then
    record PASS CLI_Usage_NoArgs "no argument prints usage and exits 0"
else
    record FAIL CLI_Usage_NoArgs "no argument: expected usage text and exit 0, got rc=$RC"
    cat "$OUT" "$WORK_DIR/usage.err"
fi

# Case 2: an unreadable/absent config file falls back to the same usage text.
"$RTAPP" "$WORK_DIR/definitely-absent.json" > "$OUT" 2>"$WORK_DIR/absent.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "rt-app <taskset.json>" "$OUT"; then
    record PASS CLI_Usage_AbsentConfigFile "absent config file falls back to usage"
else
    record FAIL CLI_Usage_AbsentConfigFile "absent config file: expected usage and exit 0, got rc=$RC"
    cat "$OUT" "$WORK_DIR/absent.err"
fi

# Case 3: malformed JSON must be rejected with the upstream diagnostic, exit 2.
printf '{ this is not json' > "$WORK_DIR/bad.json"
"$RTAPP" "$WORK_DIR/bad.json" > /dev/null 2>"$WORK_DIR/bad.err"
RC=$?
if [ "$RC" -eq 2 ] && grep -q "Error while parsing input JSON" "$WORK_DIR/bad.err"; then
    record PASS CONFIG_InvalidJson "malformed JSON is rejected with exit 2"
else
    record FAIL CONFIG_InvalidJson "malformed JSON: expected exit 2 + parse error, got rc=$RC"
    cat "$WORK_DIR/bad.err"
fi

# Case 4: a well-formed document with a wrong value type must be rejected, exit 2.
printf '%s' '{"tasks":{"T":{"run-time":1000,"period":{"type":"bogus"}}}}' > "$WORK_DIR/badtype.json"
"$RTAPP" "$WORK_DIR/badtype.json" > /dev/null 2>"$WORK_DIR/badtype.err"
RC=$?
if [ "$RC" -eq 2 ] && grep -q "Invalid type for key period" "$WORK_DIR/badtype.err"; then
    record PASS CONFIG_InvalidKeyType "wrong value type is rejected with exit 2"
else
    record FAIL CONFIG_InvalidKeyType "wrong value type: expected exit 2 + type error, got rc=$RC"
    cat "$WORK_DIR/badtype.err"
fi

echo
echo "--- real-time workload run (duration-bounded, calibration preset) ---"

# A real synthetic workload pinned to CPU 0. `calibration` is preset so the run
# does not spend up to 1000 x 1s trials measuring the loop cost, and `duration`
# makes rt-app stop and exit by itself after 3 seconds.
WORKLOAD_DIR="$WORK_DIR/workload"
mkdir -p "$WORKLOAD_DIR"
cat > "$WORKLOAD_DIR/taskset.json" <<'JSON'
{
  "global": {
    "calibration": 36,
    "lock_pages": false,
    "duration": 3
  },
  "tasks": {
    "ThreadA": {
      "run-time": 10000,
      "period": 50000,
      "policy": "SCHED_OTHER",
      "cpus": [0]
    }
  }
}
JSON

( cd "$WORKLOAD_DIR" && "$RTAPP" ./taskset.json > run.out 2> run.err )
RC=$?
RESULT_LOG="$WORKLOAD_DIR/rt-app-ThreadA-0.log"

if [ "$RC" -eq 0 ]; then
    record PASS RUN_WorkloadTerminates "duration-bounded workload runs and exits 0"
else
    record FAIL RUN_WorkloadTerminates "duration-bounded workload: expected exit 0, got rc=$RC"
    cat "$WORKLOAD_DIR/run.err"
fi

# Case 7: the preset calibration value must be honoured (no 1000-trial calibration).
if grep -q "pLoad = 36ns" "$WORKLOAD_DIR/run.err"; then
    record PASS RUN_PresetCalibrationHonoured "global.calibration skips the ns-per-loop calibration"
else
    record FAIL RUN_PresetCalibrationHonoured "global.calibration was not honoured"
    cat "$WORKLOAD_DIR/run.err"
fi

# Case 8: the thread must be pinned to the requested policy.
if grep -q "Using SCHED_OTHER policy with priority 0" "$WORKLOAD_DIR/run.err"; then
    record PASS RUN_PolicyApplied "worker thread runs under the requested SCHED_OTHER policy"
else
    record FAIL RUN_PolicyApplied "requested policy was not applied"
    cat "$WORKLOAD_DIR/run.err"
fi

# Case 9: rt-app must have written its per-thread result file with the header.
if [ -f "$RESULT_LOG" ] \
   && grep -q '^# Policy : SCHED_OTHER priority : 0' "$RESULT_LOG" \
   && grep -q '^#idx' "$RESULT_LOG"; then
    record PASS RUN_ResultLogHeader "rt-app wrote its result log with the expected header"
else
    record FAIL RUN_ResultLogHeader "result log missing or malformed"
    ls -la "$WORKLOAD_DIR" 2>/dev/null
fi

# Case 10: the result log must contain real measurements, not just headers.
ROWS=$(grep -c '^ *[0-9]' "$RESULT_LOG" 2>/dev/null || true)
[ -n "$ROWS" ] || ROWS=0
if [ "$ROWS" -ge 1 ]; then
    record PASS RUN_ResultRowsPresent "rt-app recorded $ROWS real timing measurements"
else
    record FAIL RUN_ResultRowsPresent "rt-app recorded no timing measurements"
    cat "$RESULT_LOG" 2>/dev/null
fi

# Case 11: every measurement row must be well formed (11 numeric columns).
BADROWS=$(awk '!/^#/ && NF > 0 && NF != 11 { c++ } END { print c + 0 }' "$RESULT_LOG" 2>/dev/null || true)
[ -n "$BADROWS" ] || BADROWS=0
if [ "$BADROWS" -eq 0 ]; then
    record PASS RUN_ResultRowsWellFormed "every measurement row has the 11 expected columns"
else
    record FAIL RUN_ResultRowsWellFormed "$BADROWS measurement rows have the wrong column count"
fi

echo
echo "--- HarmonyOS-specific verification ---"

SCHED_BIN="$WORK_DIR/ohos_sched_test"
if "$CC" -o "$SCHED_BIN" "$SRC_DIR/ohos_sched_test.c" 2>"$WORK_DIR/cc.log"; then
    echo "OK: ohos_sched_test.c compiled for the HarmonyOS target"
    "$SCHED_BIN" "$RTAPP" > "$WORK_DIR/sched.out" 2>&1
    RC=$?
    cat "$WORK_DIR/sched.out"
    if [ "$RC" -eq 0 ]; then
        record PASS OHOS_SchedulingApi "cpu_set_t and POSIX sched affinity API work on HarmonyOS"
        record PASS OHOS_ArtifactIsAarch64ELF "packaged rt-app is a 64-bit AArch64 ELF"
    else
        record FAIL OHOS_SchedulingApi "cpu_set_t / sched affinity API check failed (rc=$RC)"
        record FAIL OHOS_ArtifactIsAarch64ELF "AArch64 ELF verification failed (rc=$RC)"
    fi
else
    echo "ERROR: ohos_sched_test.c failed to compile"
    cat "$WORK_DIR/cc.log"
    record FAIL OHOS_SchedulingApi "ohos_sched_test.c failed to compile on the HarmonyOS target"
    record FAIL OHOS_ArtifactIsAarch64ELF "AArch64 ELF verification could not run"
fi

TOTAL=$((PASSED + FAILED + SKIPPED))
echo
echo "--- results ---"
echo "total=$TOTAL passed=$PASSED failed=$FAILED skipped=$SKIPPED ohos_cases=$OHOS_CASES ohos_passed=$OHOS_PASSED"

if [ "$FAILED" -gt 0 ]; then
    echo "=== rt-app test_package FAILED ==="
    emit true false "$TOTAL" "$PASSED" "$OHOS_CASES" "$OHOS_PASSED" "assertion_failures"
    exit 1
fi
if [ "$OHOS_CASES" -lt 1 ]; then
    echo "ERROR: no OHOS-specific case ran (>= 1 required)"
    emit true false "$TOTAL" "$PASSED" "$OHOS_CASES" "$OHOS_PASSED" "no_ohos_case"
    exit 1
fi

echo "=== all rt-app test_package cases passed ==="
emit true true "$TOTAL" "$PASSED" "$OHOS_CASES" "$OHOS_PASSED" \
     "all_cases_passed_${PASSED}_of_${TOTAL}"
exit 0
