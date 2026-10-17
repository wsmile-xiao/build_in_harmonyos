#!/bin/sh
# test_avldrums.sh — avldrums.lv2 插件 bundle 消费者验证脚本
#
# 验证 LV2 插件 bundle 安装完整：manifest.ttl / avldrums.ttl /
# 插件共享库 avldrums.so 及 SF2 采样文件存在，且 manifest.ttl 声明了
# 插件名称与库文件。作为 avldrums.lv2 可用的冒烟测试。
# 用法：test_avldrums.sh <bundle_dir>
set -u

BUNDLE="$1"

if [ ! -d "$BUNDLE" ]; then
    echo "FAIL: bundle 目录不存在: $BUNDLE"
    exit 1
fi

manifest="$BUNDLE/manifest.ttl"
ttl="$BUNDLE/avldrums.ttl"
so="$BUNDLE/avldrums.so"
sf2="$(ls "$BUNDLE"/*.sf2 2>/dev/null | head -1)"

for f in "$manifest" "$ttl" "$so"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: bundle 文件缺失: $f"
        exit 1
    fi
done

# manifest.ttl 应声明 avldrums 插件与库文件
if ! grep -q "avldrums" "$manifest" 2>/dev/null; then
    echo "FAIL: manifest.ttl 未声明 avldrums 插件: $manifest"
    exit 1
fi

# 至少一个 SF2 采样文件（鼓采样音源）
if [ -z "$sf2" ]; then
    echo "FAIL: bundle 缺少 SF2 采样文件"
    exit 1
fi

echo "PASS: avldrums.lv2 bundle 完整（manifest/ttl/so/sf2 均存在）"
echo "  - $(basename "$manifest")"
echo "  - $(basename "$ttl")"
echo "  - $(basename "$so")"
echo "  - $(basename "$sf2")"
exit 0
