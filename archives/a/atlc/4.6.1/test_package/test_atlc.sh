#!/usr/bin/env bash
# test_package/test_atlc.sh — atlc 消费测试（打包完整性 + 无参数运行）
set -euo pipefail
pkg="$1"

echo "[test] atlc 打包完整性检查"
[ -f "$pkg/bin/atlc" ] && echo "PASS: bin/atlc 存在" || { echo "FAIL: bin/atlc 缺失"; exit 1; }

echo "[test] atlc 无参数运行（打印用法）"
out=$("$pkg/bin/atlc" 2>&1) && rc=0 || rc=$?
if [ "$rc" -lt 126 ]; then
    # 正常路径：atlc 无参数时打印用法——退出码多样（实测 8）——必须有输出
    if [ -n "$out" ]; then
        echo "PASS: atlc 正常打印用法（rc=$rc）"
    else
        echo "FAIL: atlc 无输出（用法未打印）"
        exit 1
    fi
else
    # 异常路径：崩溃（≥128）/无法执行（126/127）——测试必须 FAIL
    echo "FAIL: atlc 崩溃或无法执行（rc=$rc）"
    exit 1
fi
echo "PASS: atlc smoke test OK"
