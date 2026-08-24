#!/usr/bin/env bash
# test_package/test_avarice.sh — avarice 消费测试（打包完整性 + 版本输出）
set -euo pipefail
pkg="${1:?用法: 需传 pkg 路径}"

echo "[test] avarice 打包完整性检查"
[ -f "$pkg/bin/avarice" ] && echo "PASS: bin/avarice 存在" || { echo "FAIL: bin/avarice 缺失"; exit 1; }

echo "[test] avarice --version（--version 不依赖 JTAG ICE 硬件——硬断言）"
out=$(timeout -k 2 5 "$pkg/bin/avarice" --version 2>&1) && rc=0 || rc=$?
if [ "$rc" -eq 0 ] && [ -n "$out" ]; then
    echo "PASS: avarice --version 正常（rc=$rc）"
else
    echo "FAIL: avarice --version 不可运行（rc=$rc）——二进制存在但启动失败/无输出——坏包不放行"
    exit 1
fi
echo "PASS: avarice smoke test OK"
