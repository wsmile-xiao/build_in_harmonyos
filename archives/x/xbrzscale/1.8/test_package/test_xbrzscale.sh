#!/bin/sh
# test_xbrzscale.sh — xbrzscale test_package driver (R34: really runs the
# packaged binary and the packaged static library).
#
# Usage: sh test_xbrzscale.sh <path-to-xbrzscale> <helper-dir>
#
# 9 end-to-end cases: CLI argument validation (3), PNG fixture creation (2),
# 2x and 3x file scaling with dimension verification, and the in-memory
# libxbrzscale API test. Counters track real executions (one increment per
# executed case); the HMBS markers below report exactly those counters.
# Upstream ships no test suite (see test_package/MANIFEST.yml), so the
# upstream marker declares no_tests with the audit reason.
XBRZSCALE="$1"
HELPER_DIR="$2"
WORK="${TMPDIR:-/tmp}/xbrzscale-test-$$"
TOTAL=0
PASS=0

fail() {
    echo "not ok $1 - $2"
}

pass() {
    echo "ok $1 - $2"
}

expect_rc() {
    # expect_rc <want_rc> <description> <command...>
    want="$1"
    desc="$2"
    shift 2
    TOTAL=$((TOTAL + 1))
    "$@" >/dev/null 2>&1
    rc=$?
    if [ "$rc" = "$want" ]; then
        PASS=$((PASS + 1))
        pass "$TOTAL" "$desc"
    else
        fail "$TOTAL" "$desc (want rc=$want, got rc=$rc)"
    fi
}

check_file_nonempty() {
    # check_file_nonempty <description> <file>
    desc="$1"
    file="$2"
    TOTAL=$((TOTAL + 1))
    if [ -s "$file" ]; then
        PASS=$((PASS + 1))
        pass "$TOTAL" "$desc"
    else
        fail "$TOTAL" "$desc (missing or empty: $file)"
    fi
}

mkdir -p "$WORK" || exit 1
MAKEPNG="$HELPER_DIR/test_makepng"
CHECKPNG="$HELPER_DIR/test_checkpng"
TESTLIB="$HELPER_DIR/test_lib"

expect_rc 1 "no arguments exits 1 with usage" "$XBRZSCALE"
expect_rc 1 "scale factor 1 is rejected" "$XBRZSCALE" 1 "$WORK/in.png" "$WORK/o.png"
expect_rc 1 "scale factor 7 is rejected" "$XBRZSCALE" 7 "$WORK/in.png" "$WORK/o.png"
expect_rc 0 "makepng writes 8x8 fixture" "$MAKEPNG" "$WORK/in.png"
check_file_nonempty "input fixture is non-empty" "$WORK/in.png"
expect_rc 0 "2x file scaling succeeds" "$XBRZSCALE" 2 "$WORK/in.png" "$WORK/s2.png"
expect_rc 0 "2x output is a 16x16 PNG" "$CHECKPNG" "$WORK/s2.png" 16 16
TOTAL=$((TOTAL + 1))
if "$XBRZSCALE" 3 "$WORK/in.png" "$WORK/s3.png" >/dev/null 2>&1 && "$CHECKPNG" "$WORK/s3.png" 24 24 >/dev/null 2>&1; then
    PASS=$((PASS + 1))
    pass "$TOTAL" "3x output is a 24x24 PNG"
else
    fail "$TOTAL" "3x output is a 24x24 PNG"
fi
expect_rc 0 "in-memory libxbrzscale API test (6 assertions)" "$TESTLIB"

if [ "$PASS" = "$TOTAL" ]; then
    PASSED=true
else
    PASSED=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PASSED,\"command\":\"sh test_xbrzscale.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"make -n check (no such target)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream Makefile has no check/test target and no tests directory (audited in test_package/MANIFEST.yml)\"}"
if [ "$PASSED" = "true" ]; then
    exit 0
else
    exit 1
fi
