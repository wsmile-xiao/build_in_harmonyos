#!/bin/sh
# test_xqilla.sh — xqilla test_package driver (R34: really runs the
# packaged library API test and the packaged CLI binary).
#
# Usage: sh test_xqilla.sh <path-to-xqilla> <path-to-test_xqilla>
#
# Cases: consumer API binary (parse/execute "1 to 100", 100 items), CLI -h,
# CLI query file "1 to 3" with output check, CLI missing-arg failure.
# Counters track real executions (one increment per executed case); the HMBS
# markers below report exactly those counters. Upstream ships no automated
# suite (see MANIFEST.yml), so the upstream marker declares no_tests.
XQILLA="$1"
HELPER="$2"
WORK="${TMPDIR:-/tmp}/xqilla-test-$$"
TOTAL=0
PASS=0

fail() {
    echo "not ok $1 - $2"
}

pass() {
    echo "ok $1 - $2"
}

mkdir -p "$WORK" || exit 1

# 1: consumer API test writes 100 lines (1..100)
TOTAL=$((TOTAL + 1))
if "$HELPER" >"$WORK/api.out" 2>"$WORK/api.err"; then
    LINES=$(wc -l <"$WORK/api.out" | tr -d ' ')
    FIRST=$(head -n 1 "$WORK/api.out" | tr -d '\r\n ')
    LAST=$(tail -n 1 "$WORK/api.out" | tr -d '\r\n ')
    if [ "$LINES" = "100" ] && [ "$FIRST" = "1" ] && [ "$LAST" = "100" ] && [ -s "$WORK/api.out" ]; then
        PASS=$((PASS + 1))
        pass "$TOTAL" "consumer API 1 to 100 prints 100 lines 1..100"
    else
        fail "$TOTAL" "consumer API output mismatch (lines=$LINES first=$FIRST last=$LAST)"
    fi
else
    fail "$TOTAL" "consumer API test_xqilla failed (rc=$?)"
fi

# 2: CLI -h prints usage
TOTAL=$((TOTAL + 1))
if "$XQILLA" -h >"$WORK/help.out" 2>&1; then
    if [ -s "$WORK/help.out" ]; then
        PASS=$((PASS + 1))
        pass "$TOTAL" "xqilla -h prints non-empty usage"
    else
        fail "$TOTAL" "xqilla -h produced empty output"
    fi
else
    fail "$TOTAL" "xqilla -h failed (rc=$?)"
fi

# 3: CLI executes a query file "1 to 3"
TOTAL=$((TOTAL + 1))
echo '1 to 3' >"$WORK/q13.xq"
if "$XQILLA" "$WORK/q13.xq" >"$WORK/q13.out" 2>"$WORK/q13.err"; then
    if grep -q "1" "$WORK/q13.out" && grep -q "2" "$WORK/q13.out" && grep -q "3" "$WORK/q13.out" && [ -s "$WORK/q13.out" ]; then
        PASS=$((PASS + 1))
        pass "$TOTAL" "xqilla query file 1 to 3 outputs 1 2 3"
    else
        fail "$TOTAL" "xqilla query output mismatch"
    fi
else
    fail "$TOTAL" "xqilla query file failed (rc=$?)"
fi

# 4: CLI with no query exits non-zero (usage error, must not fake-pass)
TOTAL=$((TOTAL + 1))
if "$XQILLA" >/dev/null 2>&1; then
    fail "$TOTAL" "xqilla with no args should fail but exited 0"
else
    PASS=$((PASS + 1))
    pass "$TOTAL" "xqilla with no args fails as expected"
fi

if [ "$PASS" = "$TOTAL" ]; then
    PASSED=true
else
    PASSED=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PASSED,\"command\":\"sh test_xqilla.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"make -n check (no check target)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 2.3.4 tarball has no automated make check suite; tests/ holds only manual xmark/xqts runners needing external datasets (audited in test_package/MANIFEST.yml)\"}"
if [ "$PASSED" = "true" ]; then
    exit 0
else
    exit 1
fi
