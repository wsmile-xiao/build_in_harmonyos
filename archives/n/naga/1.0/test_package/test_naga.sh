#!/bin/sh
# test_package/test_naga.sh — compile and run the naga logic API test.
#
# Invoked by test_package/conanfile.py through CONFIG_SHELL bash
# (R5: OHOS has no /bin/sh, so the shebang above is informational only —
# bash executes this file). Two phases (ncurses/6.5 precedent: compile with
# conanbuild, run with conanrun):
#   test_naga.sh compile <cc> <include-dir> <lib-dir> <src-c> <out-bin>
#   test_naga.sh run <test-bin>
#
# The test binary itself prints HMBS_TEST_PACKAGE_RESULT with the real
# executed/passed counts; the run phase fails unless the binary exits 0,
# the marker reports passed:true, and discovered/passedCount are present
# and non-zero.
set -eu

# HMBS readonly_tmp: re-export injected TMPDIR/TMP/TEMP when present so
# compiler/test children use the task tmpdir. No fallback invention,
# no mkdir, no hardcoded system temp dir.
if [ -n "${TMPDIR:-}" ]; then export TMPDIR; fi
if [ -n "${TMP:-}" ]; then export TMP; fi
if [ -n "${TEMP:-}" ]; then export TEMP; fi

mode="$1"
shift

if [ "${mode}" = "compile" ]; then
    cc="$1"
    inc="$2"
    libdir="$3"
    src_c="$4"
    out_bin="$5"
    "${cc}" -O2 -Wall "${src_c}" -I"${inc}" -L"${libdir}" -lnaga -o "${out_bin}"
    exit 0
fi

# run phase: execute the compiled binary, capture the log next to it,
# and gate on exit code plus the machine marker.
test_bin="$1"
log_file="$(dirname "${test_bin}")/test_naga.log"
set +e
"${test_bin}" > "${log_file}" 2>&1
status=$?
set -e
cat "${log_file}"
if [ "${status}" -ne 0 ]; then
    echo "FAIL: test_naga exited ${status}" >&2
    exit 1
fi
grep -q 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true' "${log_file}"
# HMBS hard gate: discovered/passedCount must be present and non-zero
# (toybox lesson: exit 0 plus a vacuous marker is not a pass).
grep -q '"discovered":[1-9]' "${log_file}"
grep -q '"passedCount":[1-9]' "${log_file}"
echo "test_naga.sh: logic tests passed (see HMBS_TEST_PACKAGE_RESULT above)"
