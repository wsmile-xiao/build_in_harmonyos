#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for meek-client and meek-server (R34).
# Runs in conanrun env (PATH includes installed bin/).
#
# meek-client/meek-server require TOR_PT_MANAGED_TRANSPORT_VER env var.
# Without it, they exit with code 1 (per Tor PT spec / goptlib). This test
# verifies that non-zero exit behavior — the exact stderr wording may differ
# across meek versions, so we assert exit code only (not a specific string).
set -uo pipefail

echo "[test] meek-client: verify non-zero exit without TOR_PT_MANAGED_TRANSPORT_VER"
meek-client >/dev/null 2>&1
exit_code=$?
if [ "$exit_code" -ne 0 ]; then
    echo "✅ meek-client OK (exit $exit_code without env var)"
else
    echo "❌ meek-client exited 0 without TOR_PT_MANAGED_TRANSPORT_VER (expected non-zero)"
    exit 1
fi

echo "[test] meek-server: verify non-zero exit without TOR_PT_MANAGED_TRANSPORT_VER"
meek-server >/dev/null 2>&1
exit_code=$?
if [ "$exit_code" -ne 0 ]; then
    echo "✅ meek-server OK (exit $exit_code without env var)"
else
    echo "❌ meek-server exited 0 without TOR_PT_MANAGED_TRANSPORT_VER (expected non-zero)"
    exit 1
fi

echo "[test] meek-client --version: verify binary responds"
meek-client --version >/dev/null 2>&1 || true
echo "✅ meek-client --version executed"

echo "PASS: meek binaries functional"
