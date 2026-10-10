#!/data/service/hnp/bin/bash
# test_package/test.sh — jenkins-cli (jcli) consumer smoke test.
# Runs in the conanrun env (PATH includes installed bin/).  Two discrete
# assertions are executed and counted explicitly (no stdout string counting);
# the HMBS_TEST_PACKAGE_RESULT marker is emitted with the REAL counts.
set -u

discovered=2
passedCount=0

if [ ! -f "$JCLI_BIN" ]; then
    echo "❌ jcli binary not found at \$JCLI_BIN=$JCLI_BIN"
    exit 1
fi

echo "[test 1/2] '$JCLI_BIN' version (expect Version: v0.0.47)"
ver_out="$("$JCLI_BIN" version 2>&1)" || {
    echo "❌ 'jcli version' failed (exit=$?)"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"jcli version\",\"discovered\":$discovered,\"passedCount\":$passedCount}"
    exit 1
}
echo "$ver_out"
if printf '%s\n' "$ver_out" | grep -F "Version: v0.0.47" >/dev/null; then
    echo "━━ PASS: version check"
    passedCount=$((passedCount + 1))
else
    echo "❌ version check: did not see 'Version: v0.0.47'"
fi

echo "[test 2/2] '$JCLI_BIN' --help (expect usage)"
help_out="$("$JCLI_BIN" --help 2>&1)" || {
    echo "❌ 'jcli --help' failed (exit=$?)"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"jcli --help\",\"discovered\":$discovered,\"passedCount\":$passedCount}"
    exit 1
}
echo "$help_out" | head -n 5
if printf '%s\n' "$help_out" | grep -E "Jenkins CLI|Usage:|jcli" >/dev/null; then
    echo "━━ PASS: help check"
    passedCount=$((passedCount + 1))
else
    echo "❌ help check: no usage text"
fi

echo "test.sh summary: $passedCount/$discovered passed"
if [ "$passedCount" -eq "$discovered" ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":$discovered,\"passedCount\":$passedCount}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":$discovered,\"passedCount\":$passedCount}"
    exit 1
fi
