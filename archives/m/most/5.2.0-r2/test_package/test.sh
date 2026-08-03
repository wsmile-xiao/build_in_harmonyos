#!/bin/sh
# test_package/test.sh — smoke test for most executable
# Runs in conanrun env with PATH extended to most's bin dir (by conanfile test())
# and LD_LIBRARY_PATH pointed at slang's lib dir (for dynamic linking).
# HMBS injects SHELL=/bin/sh (toybox) and a writable TMPDIR (OHOS /tmp is
# read-only). We reject `set -eu` (toybox) and avoid hardcoding /tmp.
#
# NOTE: most's main.c handles `--version`/`--help` by printing the banner
# (most_usage) then exit(1) — a nonzero exit code is the intended behavior,
# NOT a failure. The real assertion is that the binary starts, dynamically
# links slang (banner includes "S-Lang version"), and prints the banner.

echo "[test] most binary resolution"
if ! command -v most >/dev/null 2>&1; then
    echo "[test] most binary NOT in PATH — cannot run smoke test"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh"}'
    exit 1
fi
MOST_BIN="$(command -v most)"
echo "[test] most resolved: $MOST_BIN"

# Run the binary with --version. most prints the banner and exits 1 by design.
# Assert the banner is emitted and contains both MOST and S-Lang version strings
# — this proves the binary executes AND slang is dynamically linked at runtime.
PASS=false
echo "[test] $MOST_BIN --version"
out=$("$MOST_BIN" --version 2>&1)
rc=$?
echo "$out" | head -1
echo "[test] exit code: $rc (most exits 1 for --version by design)"

if echo "$out" | grep -q "MOST version"; then
    if echo "$out" | grep -q "S-Lang version"; then
        echo "[test] banner contains MOST version + S-Lang version — slang linked OK"
        PASS=true
    else
        echo "[test] banner has MOST version but missing S-Lang version — slang link issue"
    fi
else
    echo "[test] binary did not print the MOST version banner — startup failure"
fi

# most has no upstream test framework (audited: no gtest/pytest/make check;
# testfiles/ only holds .sl/.txt data, not assertions). Emit the no_tests
# marker per HMBS evidence gate so it does not block on missing upstream evidence.
# The manifest side (test_package/MANIFEST.yml upstream_tests_exist:false +
# upstream_test_audit) is the authority; the marker mirrors the same audit
# reason so the evidence gate can cross-verify stdout against the manifest.
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"most 5.2.0 has no upstream test framework: no gtest/pytest/criterion, no make check target; testfiles/ holds only .sl/.txt sample data, not assertions.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

if [ "$PASS" = "true" ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh"}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh"}'
    exit 1
fi
