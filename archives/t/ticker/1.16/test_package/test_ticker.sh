#!/usr/bin/env bash
# test_ticker.sh — functional tests for the ticker text scroller.
#
# Usage: bash test_ticker.sh <path-to-installed-ticker> [<qemu-aarch64>]
#
# All cases exit inside Parse_Params(), i.e. before ticker touches the
# terminal via S-Lang, so they run on headless machines too:
#   1. `ticker -h` exits 0 and prints the usage banner (this is also the
#      single upstream autopkgtest command: debian/tests/control).
#   2. `ticker --help` behaves the same (long option path via getopt_long).
#   3. `ticker` with no message prints "Must specify a message" — note the
#      upstream quirk that Usage() exits 0 even on this error path, so the
#      assertion is on the output text, not on the exit code.
#
# The script is run via `bash <path>` deliberately: HarmonyOS has no
# /bin/bash and HMDFS may drop the exec bit, so the shebang is not relied on.

set -u

TICKER_BIN="${1:-}"
TICKER_QEMU="${2:-}"

if [ -z "$TICKER_BIN" ] || [ ! -f "$TICKER_BIN" ]; then
    echo "ERROR: ticker binary not found: '${TICKER_BIN}'"
    exit 1
fi

run_ticker() {
    if [ -n "$TICKER_QEMU" ]; then
        "$TICKER_QEMU" "$TICKER_BIN" "$@"
    else
        "$TICKER_BIN" "$@"
    fi
}

pass=0
fail=0

expect_rc_and_contains() {
    # $1 case name, $2 expected rc, $3 expected substring, remaining: command
    name="$1"
    expected_rc="$2"
    expected="$3"
    shift 3
    out="$("$@" 2>&1)"
    rc=$?
    if [ "$rc" -ne "$expected_rc" ]; then
        echo "FAIL: $name exit code: expected $expected_rc, got $rc"
        fail=$((fail + 1))
        return
    fi
    if printf '%s' "$out" | grep -qF -- "$expected"; then
        echo "PASS: $name (rc=$rc) contains: $expected"
        pass=$((pass + 1))
    else
        echo "FAIL: $name (rc=$rc) missing: $expected"
        printf -- '---- actual ----\n%s\n----------------\n' "$out"
        fail=$((fail + 1))
    fi
}

expect_output_contains() {
    # $1 case name, $2 expected substring, remaining: command (rc ignored:
    # upstream Usage() exits 0 even on the error path, so text is the proof)
    name="$1"
    expected="$2"
    shift 2
    out="$("$@" 2>&1)"
    if printf '%s' "$out" | grep -qF -- "$expected"; then
        echo "PASS: $name contains: $expected"
        pass=$((pass + 1))
    else
        echo "FAIL: $name missing: $expected"
        printf -- '---- actual ----\n%s\n----------------\n' "$out"
        fail=$((fail + 1))
    fi
}

# --- Case 1: short help (== upstream autopkgtest Test-Command) ------------
expect_rc_and_contains "case1 ticker -h" 0 "Usage: ticker" run_ticker -h

# --- Case 2: long help ------------------------------------------------------
expect_rc_and_contains "case2 ticker --help" 0 "Usage: ticker" run_ticker --help

# --- Case 3: missing message (negative path, still pre-terminal) -----------
expect_output_contains "case3 no message" "Must specify a message" run_ticker

echo "SUMMARY: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
