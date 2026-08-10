#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for mdns-scan executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] mdns-scan binary exists and is executable"
command -v mdns-scan && echo "        [ok] mdns-scan found in PATH" || {
    echo "        [fail] mdns-scan not found in PATH"
    exit 1
}

echo "[step] mdns-scan starts (will timeout since it scans continuously)"
# mdns-scan runs continuously until killed; verify it starts without crash
# timeout returns 124 on timeout (expected), 141 on SIGPIPE (expected with pipe),
# or 0 if somehow exits cleanly. Any other code indicates a crash.
timeout 3 mdns-scan > /dev/null 2>&1 || rc=$?
rc=${rc:-0}
if [ "$rc" -eq 124 ] || [ "$rc" -eq 0 ] || [ "$rc" -eq 141 ]; then
    echo "        [ok] mdns-scan started and ran successfully (exit=$rc)"
else
    echo "        [fail] mdns-scan exited with code $rc"
    exit 1
fi
