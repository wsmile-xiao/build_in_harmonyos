#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for tofuenv executable
# Runs in conanrun env (PATH includes installed bin/)
# tofuenv --version only needs bash + awk, no jq required
set -eu

echo "[test] tofuenv --version"
tofuenv --version
echo "✅ --version OK"
