#!/bin/sh
# test_package/test.sh — smoke test for cpulimit binary
# Called by conanfile.py test() method via self.run()
# CPULIMIT_BIN is set by conanfile.py to the absolute path of the cpulimit binary
set -eu

CPULIMIT_BIN="${CPULIMIT_BIN:-cpulimit}"

echo "[test] Verifying cpulimit binary exists"
if [ ! -f "$CPULIMIT_BIN" ]; then
    echo "FAIL: cpulimit binary not found at $CPULIMIT_BIN"
    exit 1
fi
echo "PASS: cpulimit binary found"

echo "[test] Running cpulimit --help"
# cpulimit --help exits with code 1 by design (print_usage calls exit(1))
output=$("$CPULIMIT_BIN" --help 2>&1) || true

case "$output" in
    *"Usage"*|*"cpulimit"*)
        echo "PASS: --help output contains expected text"
        ;;
    *)
        echo "FAIL: --help output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] All smoke tests passed"
