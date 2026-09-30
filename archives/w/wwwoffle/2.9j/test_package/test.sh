#!/data/service/hnp/bin/bash
# test_package/test.sh — wwwoffle smoke test
#
# Usage: test.sh <path-to-wwwoffle-binary> [<path-to-wwwoffle-tools-binary>]
#
# The packaged wwwoffle is an ELF executable.  On OHOS the test_package runs it
# via bash with its explicit absolute package path (see test_package/conanfile.py),
# which is the canonical pattern for executable recipes (templates/test_package-executable,
# keychain).  It does NOT rely on `sh` + VirtualRunEnv PATH lookup, which fails for
# packaged ELF binaries on OHOS with "wwwoffle: inaccessible or not found".
#
# End of script emits the HMBS_TEST_PACKAGE_RESULT evidence marker; counts
# (discovered/passedCount) come from this script's single real executed case.
set -e

WWWOFFLE_BIN="${1:?usage: test.sh <wwwoffle-binary> [<wwwoffle-tools-binary>]}"
TOOLS_BIN="${2:-}"

PASSED=0
DISCOVERED=1

echo "=== $WWWOFFLE_BIN --version ==="
if "$WWWOFFLE_BIN" --version 2>&1; then
    echo "PASS: wwwoffle --version"
    PASSED=1
else
    echo "FAIL: wwwoffle --version exited non-zero"
    PASSED=0
fi

if [ -n "$TOOLS_BIN" ] && [ -x "$TOOLS_BIN" ]; then
    echo "=== $TOOLS_BIN (multi-call binary builds) ==="
    "$TOOLS_BIN" 2>&1 | head -3 || true
fi

echo "test_package: wwwoffle OK"

# HMBS_TEST_PACKAGE_RESULT 证据标记（discovered/passedCount 为本脚本真实用例计数）
if [ "$PASSED" -eq "$DISCOVERED" ] && [ "$DISCOVERED" -ge 1 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"wwwoffle --version","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASSED"
else
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"wwwoffle --version","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASSED"
    exit 1
fi
