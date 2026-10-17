#!/usr/bin/env bash
# test_cronic.sh — functional tests for the cronic cron output wrapper.
#
# Usage: bash test_cronic.sh <path-to-installed-cronic>
#
# Covers the three documented behaviours of cronic:
#   1. wrapped command succeeds with no output   -> cronic prints nothing
#   2. wrapped command exits non-zero            -> cronic prints a report
#   3. wrapped command succeeds but writes stderr -> cronic prints a report
#
# cronic is a *report wrapper*: it does not propagate the wrapped command's
# exit code, so assertions are made on the produced output, not on cronic's
# own status.
#
# The script is run via `bash <path>` deliberately: HarmonyOS has no
# /bin/bash and HMDFS may drop the exec bit, so the shebang is not relied on.

set -u

CRONIC="${1:-}"
if [ -z "$CRONIC" ] || [ ! -f "$CRONIC" ]; then
    echo "ERROR: cronic script not found: '${CRONIC}'"
    exit 1
fi

pass=0
fail=0

expect_contains() {
    # $1 case name, $2 expected substring, $3 actual output
    if printf '%s' "$3" | grep -qF -- "$2"; then
        echo "PASS: $1 contains: $2"
        pass=$((pass + 1))
    else
        echo "FAIL: $1 missing: $2"
        printf -- '---- actual ----\n%s\n----------------\n' "$3"
        fail=$((fail + 1))
    fi
}

expect_empty() {
    # $1 case name, $2 actual output
    if [ -z "$2" ]; then
        echo "PASS: $1 is empty (silent)"
        pass=$((pass + 1))
    else
        echo "FAIL: $1 expected silence, got output"
        printf -- '---- actual ----\n%s\n----------------\n' "$2"
        fail=$((fail + 1))
    fi
}

# --- Case 1: success + no output -> silent ---------------------------------
out1="$(bash "$CRONIC" true 2>&1)"
expect_empty "case1 success+silent" "$out1"

# --- Case 2: non-zero exit -> failure report -------------------------------
out2="$(bash "$CRONIC" false 2>&1)"
expect_contains "case2 nonzero-exit" "Cronic detected failure" "$out2"
expect_contains "case2 nonzero-exit" "RESULT CODE: 1" "$out2"

# --- Case 3: success + stderr output -> report -----------------------------
out3="$(bash "$CRONIC" bash -c 'printf "%s\n" "cronic-test-stderr" >&2' 2>&1)"
expect_contains "case3 success+stderr" "Cronic detected failure" "$out3"
expect_contains "case3 success+stderr" "RESULT CODE: 0" "$out3"
expect_contains "case3 success+stderr" "cronic-test-stderr" "$out3"

echo "SUMMARY: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
