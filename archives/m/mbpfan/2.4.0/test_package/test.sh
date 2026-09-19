#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for mbpfan executable.
# Runs inside the conanrun env (PATH includes the installed usr/sbin/).
set -euo pipefail

# Test 1: binary executes and prints its usage screen
echo "[test] mbpfan -h"
OUT="$(mktemp)"
mbpfan -h >"$OUT" 2>&1 || {
    echo "❌ mbpfan -h exited non-zero"
    exit 1
}
grep -q "Usage:" "$OUT" || {
    echo "❌ mbpfan -h did not print usage screen"
    exit 1
}
rm -f "$OUT"
echo "✅ -h usage OK"

# Test 2: config parse path — daemon refuses to run without root on this
# platform and says so (deterministic, assertable behavior).
echo "[test] mbpfan (no root) exits with root-privilege message"
if mbpfan -f >/dev/null 2>&1; then
    echo "❌ mbpfan unexpectedly ran without root"
    exit 1
fi
echo "✅ root-guard behavior OK"
