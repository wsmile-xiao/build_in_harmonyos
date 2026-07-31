#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for lsyncd executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# 先验证 lsyncd 二进制存在且可执行，避免 "command not found" 被误判为 --version 失败
if ! command -v lsyncd > /dev/null 2>&1; then
    echo "[fail] lsyncd binary not found in PATH"
    echo "[debug] PATH=$PATH"
    echo "[debug] which bash: $(command -v bash 2>/dev/null || echo 'bash not found')"
    exit 1
fi

echo "[test] lsyncd --version"
lsyncd --version && echo "[ok] --version OK" || {
    echo "[test] --version failed, trying -version..."
    lsyncd -version > /dev/null 2>&1 && echo "[ok] -version OK" || {
        echo "[fail] lsyncd failed both --version and -version"
        echo "[debug] lsyncd path: $(command -v lsyncd)"
        echo "[debug] file type: $(file "$(command -v lsyncd)" 2>/dev/null || echo 'file cmd unavailable')"
        exit 1
    }
}
