#!/bin/sh
# test_package/test.sh — smoke test for tlsx executable
# Runs in conanrun env (PATH includes installed bin/).
# Uses /bin/sh per HMBS platform injection (SHELL=/bin/sh,
# CONFIG_SHELL=/bin/sh); do NOT hardcode /data/service/hnp/bin/bash
# (真机诊断: [shell_getcwd] HNP bash 无法访问 HMFS/HMDFS 工作目录).
set -eu

echo "[test] tlsx -version"
if tlsx -version; then
    echo "[ok] -version"
else
    echo "[test] -version failed (exit $?), trying -help..."
    if tlsx -help > /dev/null 2>&1; then
        echo "[ok] -help"
    else
        echo "[fail] tlsx failed both -version and -help"
        exit 1
    fi
fi
