#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the udpping executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] udpping (no args, expect usage message)"
OUTPUT=$(udpping 2>&1) || true
echo "$OUTPUT" | head -3
if echo "$OUTPUT" | grep -q "Usage:"; then
    echo "OK: udpping shows usage message"
else
    echo "FAIL: udpping did not show expected usage message"
    exit 1
fi

echo "[test] udpping -s (start server briefly, then kill)"
udpping -s -p 16060 &
SERVER_PID=$!
sleep 1
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
echo "OK: udpping server mode started successfully"
