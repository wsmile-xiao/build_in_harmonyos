#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the jwhois executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary behavior.
set -eu

echo "[test] jwhois --version"
jwhois --version | grep -q "jwhois version 4.0"
echo "OK: --version reports jwhois version 4.0"

echo "[test] jwhois --help"
jwhois --help | grep -q "Usage: jwhois"
echo "OK: --help prints usage"

echo "[test] missing config file is reported and exits non-zero"
if jwhois -c /nonexistent/jwhois.conf example.com >/dev/null 2>&1; then
    echo "FAIL: missing --config must exit non-zero"
    exit 1
fi
MSG=$(jwhois -c /nonexistent/jwhois.conf example.com 2>&1 || true)
echo "$MSG" | grep -q "Unable to open"
echo "OK: missing config reported: $MSG"

echo "[test] lookup path reaches the network stage (127.0.0.1:1 connection refused)"
if jwhois -h 127.0.0.1 -p 1 -d example.com >/dev/null 2>&1; then
    echo "FAIL: connect to a closed port must fail"
    exit 1
fi
MSG=$(jwhois -h 127.0.0.1 -p 1 -d example.com 2>&1 || true)
echo "$MSG" | grep -q "Unable to connect"
echo "OK: connect refusal reported: $MSG"

echo "ALL CONSUMER TESTS PASSED"
