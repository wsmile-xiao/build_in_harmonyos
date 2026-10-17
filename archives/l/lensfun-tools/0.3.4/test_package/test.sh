#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for lensfun-tools executables.
# Runs in conanrun env (PATH includes the installed bin/, PYTHONPATH points at
# the packaged lensfun python module). lenstool exits nonzero after
# --version/--help (upstream behaviour), so the outputs are asserted instead
# of exit codes.
set -eu

echo "[test] lenstool --version"
ver_out=$(lenstool --version 2>&1 || true)
echo "$ver_out"
echo "$ver_out" | grep -q "Lenstool reference implementation for Lensfun version 0.3.4" \
    || { echo "FAIL: lenstool version output missing"; exit 1; }

echo "[test] lenstool --help"
help_out=$(lenstool --help 2>&1 || true)
echo "$help_out" | grep -q -- "--version" \
    || { echo "FAIL: lenstool help output missing"; exit 1; }

echo "[test] lensfun-add-adapter --help (exercises python3 + packaged lensfun module)"
adapter_out=$(lensfun-add-adapter --help 2>&1 || true)
echo "$adapter_out" | grep -qi "usage" \
    || { echo "FAIL: lensfun-add-adapter help output missing"; exit 1; }

echo "[test] packaged database load via lenstool camera/lens lookup"
db_out=$(lenstool -C "No Such Camera" -L "No Such Lens" 2>&1 || true)
echo "$db_out"
if echo "$db_out" | grep -q "Database could not be loaded"; then
    echo "FAIL: lenstool could not load the packaged lensfun database"
    exit 1
fi
echo "$db_out" | grep -q "No Such Camera" \
    || { echo "FAIL: unexpected lenstool lookup output"; exit 1; }

echo "PASS: lensfun-tools smoke tests"
