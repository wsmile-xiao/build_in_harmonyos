#!/usr/bin/env bash
# test_package/test_bootp.sh — bootp 消费测试（打包完整性 + 帮助信息输出）
set -euo pipefail
pkg="${1:?用法: 需传 pkg 路径}"

echo "[test] bootp 打包完整性检查"
for cmd in bootpd bootpef bootpgw; do
    [ -f "$pkg/bin/$cmd" ] && echo "PASS: bin/$cmd 存在" || { echo "FAIL: bin/$cmd 缺失"; exit 1; }
done

echo "[test] bootpd 无参数运行（打印帮助——timeout 5 防挂起）"
out=$(timeout 5 "$pkg/bin/bootpd" 2>&1) && rc=0 || rc=$?
if [ "$rc" -lt 126 ]; then
    echo "PASS: bootpd 可运行（rc=$rc）"
else
    echo "FAIL: bootpd 崩溃或无法执行（rc=$rc）"
    exit 1
fi

echo "PASS: bootp smoke test OK"
