#!/usr/bin/env bash
# test_package/test_bodr.sh — bodr 消费测试（数据仓库打包完整性）
set -euo pipefail
pkg="${1:?用法: 需传 pkg 路径}"

echo "[test] bodr 数据完整性检查"
found=""
for d in "$pkg/share/bodr" "$pkg/share"; do
    if [ -d "$d" ]; then
        n=$(find "$d" \( -name "*.xml" -o -name "*.xsl" \) -type f 2>/dev/null | wc -l || true)
        if [ "$n" -gt 0 ]; then
            found="$d"
            echo "PASS: 数据目录 $d（XML/XSL 文件 $n 个）"
            break
        fi
    fi
done
if [ -z "$found" ]; then
    echo "FAIL: bodr 数据目录缺失（share/bodr 无 XML/XSL）"
    exit 1
fi
echo "PASS: bodr smoke test OK"
