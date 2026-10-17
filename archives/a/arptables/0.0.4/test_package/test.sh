#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for arptables executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: Test must substantively depend on the tested package (run the actual binary)
set -eu

echo "[test] arptables --version (expecting version string)"
arptables --version 2>&1 | head -5
if echo "$(arptables --version 2>&1)" | grep -q "arptables v"; then
    echo "✅ arptables --version OK (version string found)"
else
    echo "❌ arptables --version did not output expected version string"
    exit 1
fi
