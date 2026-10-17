#!/data/service/hnp/bin/bash
# test_package/test_osmid.sh — smoke test for the packaged m2o/o2m binaries.
# Really executes the installed binaries (R34: the binaries ARE the API).
# --help exits 1 with cxxopts help before touching ALSA/MIDI, so no fixture
# is needed; the negative case pins a non-zero exit for an unknown option.
# A stub binary (always exit 0) or empty-output fake cannot pass all 4.
set -u

discovered=4
passed=0
failed=0

echo "[test] m2o --help (exits 1, prints 'Bridges MIDI to OSC')"
M2O_HELP=$(m2o --help 2>&1)
M2O_RC=$?
echo "$M2O_HELP" | head -n 12
if [ "$M2O_RC" -eq 1 ] && echo "$M2O_HELP" | grep -q "Bridges MIDI to OSC"; then
    passed=$((passed + 1))
    echo "[OK] m2o --help prints 'Bridges MIDI to OSC' (rc=1)"
else
    failed=$((failed + 1))
    echo "[FAIL] m2o --help rc=$M2O_RC, expected 1 + 'Bridges MIDI to OSC'"
fi

echo "[test] o2m --help (exits 1, prints 'Bridges OSC to MIDI')"
O2M_HELP=$(o2m --help 2>&1)
O2M_RC=$?
echo "$O2M_HELP" | head -n 12
if [ "$O2M_RC" -eq 1 ] && echo "$O2M_HELP" | grep -q "Bridges OSC to MIDI"; then
    passed=$((passed + 1))
    echo "[OK] o2m --help prints 'Bridges OSC to MIDI' (rc=1)"
else
    failed=$((failed + 1))
    echo "[FAIL] o2m --help rc=$O2M_RC, expected 1 + 'Bridges OSC to MIDI'"
fi

echo "[test] m2o --help output is non-empty and mentions help flag"
if [ -n "$M2O_HELP" ] && echo "$M2O_HELP" | grep -q "Display this help message"; then
    passed=$((passed + 1))
    echo "[OK] m2o help is non-empty with 'Display this help message'"
else
    failed=$((failed + 1))
    echo "[FAIL] m2o help empty or missing 'Display this help message'"
fi

echo "[test] m2o with unknown option (must exit non-zero)"
BAD_OUT=$(m2o --definitely-bogus-xyz-0x5A 2>&1)
BAD_RC=$?
echo "$BAD_OUT" | head -n 5
if [ "$BAD_RC" -ne 0 ]; then
    passed=$((passed + 1))
    echo "[OK] unknown-option path exits non-zero (rc=$BAD_RC)"
else
    failed=$((failed + 1))
    echo "[FAIL] unknown-option rc=$BAD_RC, expected non-zero"
fi

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_osmid.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_osmid.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"ctest","command":"ctest -N (n/a: no enable_testing, no add_test)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"osmid v0.8.0 audited (664 files, top-level CMakeLists with no enable_testing/add_test, no tests/ dir, no make check target; bundled external_libs oscpack/spdlog/juce unit files are third-party, not osmid tests)"}\n'
exit 0
