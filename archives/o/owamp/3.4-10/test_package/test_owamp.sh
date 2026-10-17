#!/usr/bin/env bash
# test_package/test_owamp.sh — owamp 3.4-10 consumer test (R34)
#
# 消费者视角测试：验证安装产物中的 CLI 工具存在且可执行，
# 并运行上游测试入口 owtvec（exit 0 = OWAMP 规范 Appendix B 指数偏差自检通过）。
#
# Usage: test_owamp.sh <package_prefix>
set -u

PREFIX="${1:?usage: test_owamp.sh <package_prefix>}"
BINDIR="$PREFIX/bin"
failures=0

check_exists() {
    local tool="$1"
    if [ -x "$BINDIR/$tool" ] || [ -L "$BINDIR/$tool" ]; then
        echo "  [PASS] $tool present"
    else
        echo "  [FAIL] $tool missing: $BINDIR/$tool"
        failures=$((failures + 1))
    fi
}

echo "== owamp consumer test (prefix=$PREFIX) =="

# 7 个实际安装工具（含 3 个符号链接自 owping）
check_exists owampd
check_exists owping
check_exists owstats
check_exists owfetch
check_exists owup
check_exists powstream
check_exists owtvec

# 上游测试入口：owtvec 自检（exit 0 = PASS）
echo "== running upstream test entry: owtvec =="
"$BINDIR/owtvec"
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "  [PASS] owtvec self-check exited 0"
else
    echo "  [FAIL] owtvec self-check exited $rc"
    failures=$((failures + 1))
fi

echo "== $failures failure(s) =="
exit "$failures"
