#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for coreutils executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] echo --version"
echo --version && echo "✅ echo --version OK" || {
    echo "[test] echo --version failed"
    exit 1
}

echo "[test] cat piped input"
echo "hello world" | cat - && echo "✅ cat piped OK" || {
    echo "[test] cat piped failed"
    exit 1
}

echo "[test] sort piped input"
printf "banana\napple\ncherry\n" | sort && echo "✅ sort piped OK" || {
    echo "[test] sort piped failed"
    exit 1
}

echo "[test] wc piped input"
echo "test line" | wc -l && echo "✅ wc piped OK" || {
    echo "[test] wc piped failed"
    exit 1
}

echo "[test] date"
date && echo "✅ date OK" || {
    echo "[test] date failed"
    exit 1
}

echo "[test] expr compound regex"
expr 'abc123' : '.*[0-9]' && echo "✅ expr OK" || {
    echo "[test] expr failed"
    exit 1
}

echo "All tests passed ✅"
