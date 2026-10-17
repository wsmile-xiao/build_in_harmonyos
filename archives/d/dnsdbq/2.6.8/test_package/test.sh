#!/bin/sh
# test_package/test.sh — dnsdbq 2.6.8 行为契约测试（离线、确定性）
#
# R34：真实执行被测包安装出来的 bin/dnsdbq 并断言其输出，
# 不是 print-only / pass-only 空壳。二进制缺失或输出不匹配即失败。
#
# 用法: sh test.sh <dnsdbq 可执行文件路径>
# 退出码 0 = 全部检查通过；非 0 = 有检查失败。
set -u

DNSDBQ="${1:?usage: test.sh <path-to-dnsdbq>}"

if [ ! -f "$DNSDBQ" ]; then
    echo "[FAIL] bin/dnsdbq 不存在: $DNSDBQ"
    exit 1
fi

CHECKED=0
PASSED=0

ok() {
    CHECKED=$((CHECKED + 1))
    PASSED=$((PASSED + 1))
    echo "[PASS] $1"
}

no() {
    CHECKED=$((CHECKED + 1))
    echo "[FAIL] $1"
    echo "------- actual output -------"
    printf '%s\n' "$2"
    echo "-----------------------------"
}

# T1: -h 输出 usage 行（证明二进制可执行 + CLI 入口正常）
OUT1="$("$DNSDBQ" -h 2>&1)"
if printf '%s' "$OUT1" | grep -qi "usage"; then
    ok "T1: -h 输出 usage 行"
else
    no "T1: -h 未输出 usage 行" "$OUT1"
fi

# T2: -h 输出主要选项表（-p dns|json|csv 输出格式声明）
if printf '%s' "$OUT1" | grep -q '\-p dns|json|csv'; then
    ok "T2: -h 列出 -p dns|json|csv 输出格式选项"
else
    no "T2: -h 未列出 -p dns|json|csv 选项" "$OUT1"
fi

echo "checked=$CHECKED passed=$PASSED"
[ "$PASSED" = "$CHECKED" ] && exit 0 || exit 1
