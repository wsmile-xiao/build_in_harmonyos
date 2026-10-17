#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for buildcache executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] buildcache --version"
if buildcache --version; then
    echo "[test] --version OK"
else
    echo "[test] --version failed, trying --help..."
    if buildcache --help > /dev/null 2>&1; then
        echo "[test] --help OK"
    else
        echo "[test] FAIL: buildcache failed both --version and --help"
        exit 1
    fi
fi

echo "[test] buildcache -h (help)"
buildcache -h > /dev/null && echo "[test] -h OK"
