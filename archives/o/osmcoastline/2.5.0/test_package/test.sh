#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for osmcoastline executable
# Runs in conanrun env (PATH includes installed bin/)
#
# NOTE (OHOS CI worker): buildbot 的 stdin 是打开的管道，nodegrid2opl 等
# 从 STDIN 读取输入的程序会永久阻塞等待 EOF → 整条 CI 超时。
# 因此所有二进制调用统一重定向 stdin 为 /dev/null，并加 timeout 保险。
set -eu

# helper: run a binary's --version with stdin closed and a timeout guard
smoke_version() {
    local name="$1"
    echo "[test] $name --version"
    if timeout 30 "$name" --version < /dev/null > /dev/null 2>&1; then
        echo "PASS: $name --version OK"
        return 0
    fi
    echo "FAIL: $name --version failed"
    return 1
}

smoke_version osmcoastline
smoke_version osmcoastline_filter
smoke_version nodegrid2opl

echo "ALL_SMOKE_TESTS_PASS"
