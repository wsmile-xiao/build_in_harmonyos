#!/usr/bin/env bash
# test_package/test_avrp.sh — avrp 消费测试（打包完整性 + 无参数运行）
set -euo pipefail
pkg="$1"

echo "[test] avrp 打包完整性检查"
[ -f "$pkg/bin/avrp" ] && echo "PASS: bin/avrp 存在" || { echo "FAIL: bin/avrp 缺失"; exit 1; }

echo "[test] avrp 无参数运行（打印用法）"
# aireview P2-2：set -e 下 avrp 非零退出会提前中止（rc=1 正常路径不可达）——
# 改用 `&& rc=0 || rc=$?` 保留真实退出码（复合语句不受 set -e 影响）
out=$("$pkg/bin/avrp" 2>&1) && rc=0 || rc=$?
if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
    # 正常路径：avrp 无参数时打印用法并退出 0/1——必须有输出
    if [ -n "$out" ]; then
        echo "PASS: avrp 正常打印用法（rc=$rc）"
    else
        echo "FAIL: avrp 无输出（用法未打印）"
        exit 1
    fi
else
    # 异常路径：崩溃（≥128）/无法执行（126/127）——测试必须 FAIL
    echo "FAIL: avrp 崩溃或无法执行（rc=$rc）"
    exit 1
fi
echo "PASS: avrp smoke test OK"
