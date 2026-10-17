#!/usr/bin/env bash
# test_package/test.sh — smoke test for gtimeout executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] gtimeout --version"
gtimeout --version && echo "✅ gtimeout --version OK" || {
    echo "[test] gtimeout --version failed"
    exit 1
}

echo "[test] gtimeout runs a quick command"
gtimeout 5 echo "hello from gtimeout" && echo "✅ gtimeout command OK" || {
    echo "[test] gtimeout command failed"
    exit 1
}

echo "[test] gtimeout kills a long-running command"
rc=0
gtimeout 1 sleep 10 || rc=$?
if [ "$rc" -ne 124 ]; then
    echo "[test] expected exit 124 (timeout kill), got $rc"
    exit 1
fi
echo "✅ gtimeout timeout kill OK (exit code 124)"

echo "[test] gtimeout --preserve-status"
rc=0
gtimeout --preserve-status 1 sleep 10 || rc=$?
if [ "$rc" -ne 143 ]; then
    echo "[test] expected exit 143 (preserved SIGTERM status), got $rc"
    exit 1
fi
echo "✅ gtimeout --preserve-status OK (exit code 143)"

echo "All tests passed ✅"
