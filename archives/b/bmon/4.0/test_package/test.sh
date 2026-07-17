#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the bmon executable.
# Runs in the conanrun environment (PATH includes the installed bin/).
set -euo pipefail

echo "[test] bmon --version"
bmon --version | grep -q "bmon 4.0"
echo "OK: version"

# Functional test: exercise the /proc/net/dev (in_proc) input module and the
# ascii output module. Run bounded, then verify real interface statistics were
# read (the table header is printed once stats are collected).
echo "[test] bmon reads /proc/net/dev via in_proc"
out="$( { bmon -i proc -o ascii -r 1 -R 1 & p=$!; sleep 2; kill "$p" 2>/dev/null; wait "$p" 2>/dev/null; } || true )"
echo "$out" | grep -q "Interfaces"
echo "OK: proc input produced interface statistics"

echo "ALL TESTS PASSED"
