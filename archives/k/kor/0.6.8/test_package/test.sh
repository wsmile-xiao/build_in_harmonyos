#!/bin/sh
# test_package/test.sh — smoke test for kor executable
# Runs in conanrun env (PATH includes installed bin/).
# Uses /bin/sh per HMBS platform injection (SHELL=/bin/sh,
# CONFIG_SHELL=/bin/sh).
set -eu

echo "[test] kor version"
if kor version; then
    echo "[ok] kor version"
else
    echo "[test] -version failed (exit $?), trying --help..."
    if kor --help > /dev/null 2>&1; then
        echo "[ok] kor --help"
    else
        echo "[fail] kor failed both version and --help"
        exit 1
    fi
fi
