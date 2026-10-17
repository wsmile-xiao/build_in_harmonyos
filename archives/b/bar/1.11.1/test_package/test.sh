#!/usr/bin/env bash
# test_package/test.sh — smoke test for bar executable
# bar shows information about a data transfer stream.
# Runs in conanrun env (PATH includes installed bin/).
set -uo pipefail

echo "[test] bar --version (version check)"
# Note: upstream bar prints the version and returns exit code 1, so check
# the output content rather than the pipeline exit status.
ver="$(bar --version 2>&1)"
if printf '%s' "$ver" | grep -q "bar version"; then
    echo "PASS: bar --version OK"
else
    echo "FAIL: bar --version produced unexpected output: [$ver]"
    exit 1
fi

echo "[test] bar pipe transfer test (printf | bar | cat)"
out="$(printf 'hello world' | bar 2>/dev/null | cat)"
if [ "$out" = "hello world" ]; then
    echo "PASS: bar copied the stream intact"
else
    echo "FAIL: bar produced unexpected output: [$out]"
    exit 1
fi
