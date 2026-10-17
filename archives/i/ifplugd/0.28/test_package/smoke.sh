#!/bin/sh
# test_package/smoke.sh - behavior test for packaged ifplugd/ifplugstatus.
# No root, no interfaces, no routes touched: only -h/-v and bad-option paths.
#
# Counting contract (HMBS hard gate): exactly 6 deterministic scenarios.
# PASS is incremented exactly once per scenario; sub-checks inside a scenario
# only fail it (no extra increments), and no stdout string-counting or
# arithmetic fix-ups are used. Final state always satisfies
# passed + failed == executed and executed <= discovered.
set -eu
IFPLUGD="$1"
IFPLUGSTATUS="$2"
TOTAL=6
PASS=0

emit_markers() {
    # $1=true|false (overall), $2=passedCount so far
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$1,\"command\":\"sh smoke.sh\",\"discovered\":$TOTAL,\"passedCount\":$2}"
    echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"autotools\",\"command\":\"make check\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 0.28 ships no tests dir and no TESTS/check_PROGRAMS in any Makefile.am (audit: test_package/MANIFEST.yml)\"}"
}

fail() {
    # $1=label
    echo "FAIL: $1"
    emit_markers false "$PASS"
    exit 1
}

check_contains() {
    # $1=output $2=needle $3=label (sub-check: no counter change)
    case "$1" in
        *"$2"*) echo "ok: $3";;
        *) fail "$3 (missing '$2')";;
    esac
}

echo "[test 1/6] binaries exist and are executable"
[ -x "$IFPLUGD" ] || fail "$IFPLUGD not executable"
[ -x "$IFPLUGSTATUS" ] || fail "$IFPLUGSTATUS not executable"
echo "PASS [1/6]: both binaries present and executable"
PASS=$((PASS+1))

echo "[test 2/6] ifplugd -h full usage banner"
OUT="$("$IFPLUGD" -h 2>&1 || true)"
check_contains "$OUT" "Network Interface Plug Detection Daemon" "ifplugd -h banner title"
check_contains "$OUT" "Usage:" "ifplugd -h usage line"
check_contains "$OUT" "--iface" "ifplugd -h iface option"
echo "PASS [2/6]: ifplugd -h banner"
PASS=$((PASS+1))

echo "[test 3/6] ifplugd -v version"
OUT="$("$IFPLUGD" -v 2>&1 || true)"
check_contains "$OUT" "0.28" "ifplugd -v prints 0.28"
echo "PASS [3/6]: ifplugd -v version"
PASS=$((PASS+1))

echo "[test 4/6] ifplugd bad option rejected"
set +e
OUT="$("$IFPLUGD" --definitely-not-an-option 2>&1)"
RC=$?
set -e
[ "$RC" -ne 0 ] || fail "ifplugd accepted unknown option (expected non-zero exit)"
check_contains "$OUT" "unrecognized option" "ifplugd unknown-option diagnostic"
echo "PASS [4/6]: ifplugd rejects unknown option"
PASS=$((PASS+1))

echo "[test 5/6] ifplugstatus -h usage"
OUT="$("$IFPLUGSTATUS" -h 2>&1 || true)"
check_contains "$OUT" "[options] [INTERFACE]" "ifplugstatus -h usage"
check_contains "$OUT" "--help" "ifplugstatus -h help option"
echo "PASS [5/6]: ifplugstatus -h usage"
PASS=$((PASS+1))

echo "[test 6/6] ifplugstatus bad option rejected"
set +e
OUT="$("$IFPLUGSTATUS" --definitely-not-an-option 2>&1)"
RC=$?
set -e
[ "$RC" -ne 0 ] || fail "ifplugstatus accepted unknown option (expected non-zero exit)"
check_contains "$OUT" "unrecognized option" "ifplugstatus unknown-option diagnostic"
echo "PASS [6/6]: ifplugstatus rejects unknown option"
PASS=$((PASS+1))

echo "SUMMARY: $PASS/$TOTAL behavior scenarios passed"
emit_markers true "$PASS"
