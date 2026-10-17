#!/bin/sh
# test_package 真实测试源：执行安装后的 irqbalance 并核验版本输出。
# irqbalance 为 CLI 守护进程（application 包），无库 API 可链接，
# 消费者验证走二进制执行（R34 实质测试）。
# 注：上游 --version 分支退出码为 1（irqbalance.c: version(); exit(1)），
# 属上游语义而非失败，故先捕获输出再判定，避免 pipefail 误报。
set -euo pipefail
BIN="${1:-irqbalance}"
VER="$("$BIN" --version 2>&1 || true)"
case "$VER" in
    *"irqbalance version 1.9.4"*)
        echo "PASS: irqbalance --version -> 1.9.4"
        ;;
    *)
        echo "FAIL: irqbalance --version 输出未包含版本号: $VER" >&2
        exit 1
        ;;
esac
