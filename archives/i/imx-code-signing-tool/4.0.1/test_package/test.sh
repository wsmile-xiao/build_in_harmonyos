#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for imx-code-signing-tool (CST) 4.0.1
# Runs in conanrun env (PATH includes installed bin/).
set -eu

echo "[test] cst --version"
VERSION_OUT="$(cst --version)"
echo "$VERSION_OUT"
echo "$VERSION_OUT" | grep -q "4.0.1" || {
    echo "❌ cst --version did not report 4.0.1"
    exit 1
}
echo "✅ cst --version OK"

echo "[test] cst --help"
cst --help > /dev/null 2>&1 || cst -h > /dev/null 2>&1 || {
    echo "❌ cst --help failed"
    exit 1
}
echo "✅ cst --help OK"

echo "[test] srktool (usage)"
SRK_OUT="$(srktool 2>&1 || true)"
echo "$SRK_OUT" | grep -qi "Usage" || {
    echo "❌ srktool did not print usage"
    exit 1
}
echo "✅ srktool usage OK"
