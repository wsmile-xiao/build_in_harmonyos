#!/bin/sh
# test.sh — weupnp 0.1.4 consumer test driver.
#
# POSIX sh on purpose: the OHOS worker has no /bin/bash (only /bin/sh), and the
# CI runner invokes this script through `sh`.
#
# usage: sh test.sh <java> <javac> <packaged-jar> <test-source-dir> <work-dir>
#
# Compiles TestWeupnp.java against the *packaged* JAR and runs it. Emits a
# machine-readable HMBS_TEST_PACKAGE_RESULT marker for the CI reporter.

set -u

JAVA="${1:?java executable required}"
JAVAC="${2:?javac executable required}"
JAR="${3:?packaged JAR required}"
SRC_DIR="${4:?test source folder required}"
WORK_DIR="${5:?work folder required}"

LOG="$WORK_DIR/weupnp-test.log"
CLASSES="$WORK_DIR/classes"
# The work folder is disposable: fresh at entry, removed on every exit path so
# no build product is ever left behind in the recipe tree.
rm -rf "$WORK_DIR"
mkdir -p "$CLASSES"
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM

emit() {
    # $1=executed $2=passed $3=discovered $4=passedCount $5=ohosCases $6=ohosPassed $7=reason
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\": $1, \"passed\": $2, \"discovered\": $3, \"passedCount\": $4, \"ohosCases\": $5, \"ohosPassed\": $6, \"command\": \"sh test.sh\", \"reason\": \"$7\"}"
}

if [ ! -f "$JAR" ]; then
    echo "ERROR: packaged JAR not found: $JAR"
    emit false false 0 0 0 0 "jar_missing"
    exit 1
fi

echo "=== weupnp 0.1.4 test_package ==="
echo "jar   : $JAR"
echo "java  : $JAVA"
echo "javac : $JAVAC"

echo "--- compiling TestWeupnp.java against the packaged JAR ---"
"$JAVAC" -nowarn -cp "$JAR" -d "$CLASSES" "$SRC_DIR/TestWeupnp.java"
compile_rc=$?
if [ "$compile_rc" -ne 0 ]; then
    echo "ERROR: javac failed (exit $compile_rc) — the consumer test must compile against the packaged JAR"
    emit false false 0 0 0 0 "javac_failed"
    exit 1
fi
echo "OK: consumer test compiled against the packaged JAR"

echo "--- running the weupnp consumer test suite ---"
"$JAVA" -Dweupnp.jar="$JAR" -cp "$JAR:$CLASSES" TestWeupnp > "$LOG" 2>&1
run_rc=$?
cat "$LOG"

total=$(grep -c -E '^(PASS|FAIL|SKIP)' "$LOG")
passed=$(grep -c '^PASS' "$LOG")
failed=$(grep -c '^FAIL' "$LOG")
skipped=$(grep -c '^SKIP' "$LOG")
ohos_cases=$(grep -c -E '^(PASS|FAIL|SKIP) +OHOS_' "$LOG")
ohos_passed=$(grep -c -E '^PASS +OHOS_' "$LOG")

echo "--- results ---"
echo "total=$total passed=$passed failed=$failed skipped=$skipped ohos_cases=$ohos_cases ohos_passed=$ohos_passed exit=$run_rc"

if [ "$failed" -gt 0 ] || [ "$run_rc" -ne 0 ]; then
    emit true false "$total" "$passed" "$ohos_cases" "$ohos_passed" "assertion_failures"
    exit 1
fi
if [ "$ohos_cases" -lt 1 ]; then
    echo "ERROR: no OHOS-specific case ran (>= 1 required)"
    emit true false "$total" "$passed" "$ohos_cases" "$ohos_passed" "no_ohos_case"
    exit 1
fi

echo "=== all weupnp test_package cases passed ==="
emit true true "$total" "$passed" "$ohos_cases" "$ohos_passed" \
     "all_cases_passed_${passed}_of_${total}_with_${skipped}_skipped"
exit 0
