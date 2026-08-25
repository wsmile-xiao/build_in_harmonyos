#!/bin/sh
# test_package/test.sh — esniper 2.35.0 消费者测试 (R34)
# 实质执行 esniper 二进制的多个子命令并校验退出码与输出。
# esniper 上游无测试套件（纯命令行工具），此处补全 3 项断言测试。
#
# 断言来源（源码 esniper.c main()）：
#   -v → printVersion() + exit(0)        (esniper.c:727-729)
#   -h → usage(USAGE_LONG) + exit(1)     (esniper.c:571-587, 627)
#   无参 → "no auctions specified" + exit(1) (esniper.c:780-783)
set -u

ESNIPER_BIN="${1:-esniper}"
PASS=0
TOTAL=3

# ── Test 1: esniper -v (版本输出，exit 0) ──
out=$("$ESNIPER_BIN" -v 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && echo "$out" | grep -q "version 2.35.0"; then
    echo "PASS [1/$TOTAL]: esniper -v -> exit 0, version string present"
    PASS=$((PASS + 1))
else
    echo "FAIL [1/$TOTAL]: esniper -v -> exit=$rc (expected 0)"
fi

# ── Test 2: esniper -h (帮助输出，exit 1) ──
out=$("$ESNIPER_BIN" -h 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && echo "$out" | grep -q "usage:"; then
    echo "PASS [2/$TOTAL]: esniper -h -> exit 1, usage help printed"
    PASS=$((PASS + 1))
else
    echo "FAIL [2/$TOTAL]: esniper -h -> exit=$rc (expected 1)"
fi

# ── Test 3: esniper (无参，错误提示，exit 1) ──
out=$("$ESNIPER_BIN" 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && echo "$out" | grep -q "no auctions specified"; then
    echo "PASS [3/$TOTAL]: esniper (no args) -> exit 1, error message present"
    PASS=$((PASS + 1))
else
    echo "FAIL [3/$TOTAL]: esniper (no args) -> exit=$rc (expected 1)"
fi

echo ""
echo "Result: $PASS/$TOTAL tests passed ($((PASS * 100 / TOTAL))%)"

# 任一失败则返回 1，确保 CI 门禁不产生假阳性
[ "$PASS" -ne "$TOTAL" ] && exit 1
exit 0
