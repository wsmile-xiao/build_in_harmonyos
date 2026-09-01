#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for open-adventure executables
# Runs in conanrun env (PATH includes installed bin/)
set -uo pipefail

# advent/cheat have no --version flag. -h is unrecognized but produces
# usage output and exits 1 — verifies the binary is executable.
echo "[test] advent -h"
advent -h < /dev/null 2>&1 || rc=$?
if [ "${rc:-0}" -gt 1 ]; then echo "❌ advent exit $rc"; exit 1; fi
echo "✅ advent executable works"

echo "[test] cheat -h"
cheat -h < /dev/null 2>&1 || rc=$?
if [ "${rc:-0}" -gt 1 ]; then echo "❌ cheat exit $rc"; exit 1; fi
echo "✅ cheat executable works"
