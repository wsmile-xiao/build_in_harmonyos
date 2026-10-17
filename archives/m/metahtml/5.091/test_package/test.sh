#!/bin/sh
# metahtml 5.091 消费者测试件（test_package，L0c 白名单扩展名 .sh）
# 真实执行包内安装的 mhc 渲染最小 MHTML 语料，对输出做逐字节(cmp)+逐行(grep)断言。
# 期望值来自设备实测（2026-09-27）：rc=0，输出恰两行、51 字节、尾随换行。
# 运行环境：Conan VirtualRunEnv（PATH/LD_LIBRARY_PATH 已指向被测包与 gdbm 依赖）。
# 退出码：全部断言通过 -> 0；任一失败 -> 1。

set -u

PASSED=0
FAILED=0

ok() {
    PASSED=$((PASSED + 1))
    echo "PASS[$PASSED] $1"
}

ng() {
    FAILED=$((FAILED + 1))
    echo "FAIL[$FAILED] $1"
    if [ -f mhc.err ]; then
        echo "--- stderr ---"
        cat mhc.err
    fi
    if [ -f mhc.out ]; then
        echo "--- stdout ---"
        cat mhc.out
    fi
}

# A1: 被测二进制可经 conanrun PATH 定位（动态依赖齐全的必要面）
if command -v mhc >/dev/null 2>&1; then
    ok "mhc 可由 PATH 定位（VirtualRunEnv 生效）"
else
    ng "mhc 不在 PATH（VirtualRunEnv 未生效?）"
    echo "SUMMARY total=1 passed=0 failed=1"
    exit 1
fi

# A2: 语料渲染端到端，输出与期望逐字节一致（notes.md 语料同构语法）
printf "Result: consumer-smoke: <add 40 2>\nResult: consumer-and: <and 1 1>\n" > smoke.in
printf "Result: consumer-smoke: 42\nResult: consumer-and: 1\n" > smoke.expected
if mhc smoke.in > mhc.out 2> mhc.err && cmp -s mhc.out smoke.expected; then
    ok "逐字节断言: mhc 渲染 <add 40 2>=>42 且 <and 1 1>=>1"
else
    ng "mhc 渲染输出与期望不一致（逐字节 cmp）"
    echo "SUMMARY total=2 passed=$PASSED failed=$FAILED"
    exit 1
fi

# A3: 逐行断言（两行 Result: 均在场且值正确）
if grep -q "^Result: consumer-smoke: 42$" mhc.out && grep -q "^Result: consumer-and: 1$" mhc.out; then
    ok "逐行断言: Result 两行齐且值正确"
else
    ng "Result 行逐行断言失败"
fi

TOTAL=$((PASSED + FAILED))
echo "SUMMARY total=$TOTAL passed=$PASSED failed=$FAILED"
if [ "$FAILED" -ne 0 ]; then
    exit 1
fi
rm -f smoke.in smoke.expected mhc.out mhc.err
exit 0
