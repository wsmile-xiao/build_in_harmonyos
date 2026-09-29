#!/bin/sh
# libservicelog consumer E2E: drives the six upstream scenario tests
# (upstream src/tests/tests/test-00X-*_event, shipped inside the package
# under share/libservicelog/upstream-tests/) against the INSTALLED shared
# library, using upstream's own test driver test_libservicelog.c compiled
# in test_package.
#
# POSIX port of the upstream bash runner src/tests/run_tests with the same
# semantics: every scenario is truncate_events + log_event + dump +
# timestamp-tolerant comparison (upstream diff_with_result_without_timestamp,
# ported to cmp_tolerant.py because the device lacks GNU `diff -y`).
# test-006-truncate_event does truncate / log / truncate with no diff.
#
# Usage: run_upstream_tests.sh <test_binary> <expected_dir> <cmp.py>
# Env:    SL_TEST_DB  writable DB path (SERVICELOG_DB is inherited from
#                     the caller; the env override is exercised here)
set -u

BIN=$1
RESULTS=$2
CMP=$3

if [ ! -x "$BIN" ]; then
    echo "Fatal: cannot execute '$BIN'"
    exit 1
fi
if [ -z "${SL_TEST_DB:-}" ]; then
    echo "Fatal: SL_TEST_DB must point to a writable db path"
    exit 1
fi

TMPDIR=${TMPDIR:-/tmp}
OUT=$(mktemp -d "${TMPDIR}/libservicelog-tp.XXXXXX") || { echo "mktemp failed"; exit 1; }
trap 'rm -rf "$OUT"' EXIT

fails=0

# scenario name:event type, same pairs as upstream run_tests glob order
for pair in "001-log_basic_event:1" "002-log_os_event:2" "003-log_rtas_event:3" \
            "004-log_encl_event:4" "005-log_bmc_event:5"; do
    name=${pair%%:*}
    ev=${pair##*:}
    # upstream truncate_events: clear, then verify dump is empty
    if ! "$BIN" 7 >/dev/null 2>&1; then
        echo "FAIL $name (truncate)"; fails=1; continue
    fi
    if ! "$BIN" 6 > "$OUT/$name.trunc.out" 2>/dev/null; then
        echo "FAIL $name (truncate dump)"; fails=1; continue
    fi
    if [ -s "$OUT/$name.trunc.out" ]; then
        echo "FAIL $name (dump not empty after truncate)"; fails=1; continue
    fi
    if ! "$BIN" "$ev" >/dev/null 2>&1; then
        echo "FAIL $name (log)"; fails=1; continue
    fi
    if ! "$BIN" 6 > "$OUT/$name.out" 2> "$OUT/$name.err"; then
        echo "FAIL $name (dump)"; fails=1; continue
    fi
    if ! python3 "$CMP" "$RESULTS/test-$name.result.out" "$OUT/$name.out"; then
        echo "FAIL $name (comparison)"; fails=1; continue
    fi
    echo "PASS $name"
done

# test-006-truncate_event: clear, log one BMC event, clear again
if "$BIN" 7 >/dev/null 2>&1 && "$BIN" 5 >/dev/null 2>&1 && "$BIN" 7 >/dev/null 2>&1 \
   && "$BIN" 6 > "$OUT/006.trunc.out" 2>/dev/null && [ ! -s "$OUT/006.trunc.out" ]; then
    echo "PASS 006-truncate_event"
else
    echo "FAIL 006-truncate_event"; fails=1
fi

if [ "$fails" -ne 0 ]; then
    echo "SUITE FAIL"
    exit 1
fi
echo "SUITE PASS: 6/6 upstream scenarios"
exit 0
