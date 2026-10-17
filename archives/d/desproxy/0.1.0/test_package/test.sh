#!/data/service/hnp/bin/bash
# test_package/test.sh — desproxy 0.1.0 冒烟测试
# 在 conanrun 环境执行（PATH 含已安装 bin/）。
# 上游无测试套件（Makefile 无 check/test 目标），此处为适配后补全的
# 消费者级冒烟测试：逐一执行 5 个二进制，验证可运行并输出版本 banner。
set -euo pipefail

check_bin() {
    local name="$1"
    echo "[test] ${name} version banner"
    # 无参数运行时打印版本 banner + Usage 后退出（exit 0）
    local output
    output=$("${name}" 2>&1 || true)
    if echo "$output" | grep -q "${name}" && echo "$output" | grep -q "0.1.0"; then
        echo "✅ ${name} OK"
    else
        echo "❌ ${name} failed"
        echo "$output"
        exit 1
    fi
}

check_bin desproxy
check_bin desproxy-inetd
check_bin desproxy-socksserver
check_bin desproxy-dns
check_bin socket2socket

echo "✅ desproxy 0.1.0 全部 5 个二进制冒烟测试通过"
