#!/bin/sh
# test_package/test.sh — functional test for the debsig-verify executable
# Runs in conanrun env (PATH includes the installed bin/).
# Real executions, all asserting exit codes and non-empty output:
#   TC1: debsig-verify binary present and executable
#   TC2: `debsig-verify --version` exits 0 with non-empty output
#   TC3: `debsig-verify --help` exits 0 with non-empty output
#   TC4: missing input file is rejected (non-zero exit, non-empty diagnostic)
set -u

discovered=4
passed=0
failed=0

# TC1
bin="$(command -v debsig-verify 2>/dev/null)"
if [ -n "$bin" ] && [ -x "$bin" ]; then
    passed=$((passed + 1))
    echo "[ok] TC1: debsig-verify binary present and executable ($bin)"
else
    failed=$((failed + 1))
    echo "[fail] TC1: debsig-verify binary missing or not executable"
fi

# TC2
out="$(debsig-verify --version 2>&1)"
rc=$?
if [ $rc -eq 0 ] && [ -n "$out" ]; then
    passed=$((passed + 1))
    echo "[ok] TC2: --version exits 0 with output: $out"
else
    failed=$((failed + 1))
    echo "[fail] TC2: --version failed (rc=$rc, output: $out)"
fi

# TC3
out="$(debsig-verify --help 2>&1)"
rc=$?
if [ $rc -eq 0 ] && [ -n "$out" ]; then
    passed=$((passed + 1))
    echo "[ok] TC3: --help exits 0 with non-empty output"
else
    failed=$((failed + 1))
    echo "[fail] TC3: --help failed (rc=$rc)"
fi

# TC4
out="$(debsig-verify /nonexistent-debsig-test.deb 2>&1)"
rc=$?
if [ $rc -ne 0 ] && [ -n "$out" ]; then
    passed=$((passed + 1))
    echo "[ok] TC4: missing input rejected (rc=$rc)"
else
    failed=$((failed + 1))
    echo "[fail] TC4: missing input unexpectedly accepted (rc=$rc)"
fi

if [ $failed -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 1
fi
