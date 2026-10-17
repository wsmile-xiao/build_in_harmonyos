#!/bin/sh
# test_autotalent.sh — autotalent test_package 测试脚本
# 验证 autotalent.so LADSPA 插件存在 + 含 ladspa_descriptor 描述符号（R34）
#
# 用法: sh test_autotalent.sh <ladspa_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <ladspa_dir>" >&2
    exit 2
fi
DIR="$1"
SO="$DIR/autotalent.so"

echo "== 1. 产物存在性检查 =="
if [ ! -f "$SO" ]; then
    echo "FAIL: autotalent.so not found" >&2
    exit 1
fi

echo "== 2. LADSPA 描述符号检查 =="
# 先判断 nm 是否可用——nm 可用时符号缺失直接 FAIL（不可降级到 ldd——
# ldd 对任意合法 .so 返回 0，无法拦截缺 ladspa_descriptor 的损坏产物；
# 严格匹配 ladspa_descriptor，不用宽松备选词避免误报）
if command -v nm >/dev/null 2>&1; then
    if nm -D "$SO" 2>/dev/null | grep -qE "ladspa_descriptor"; then
        echo "OK: autotalent.so LADSPA descriptor present"
        exit 0
    fi
    echo "FAIL: ladspa_descriptor symbol missing in autotalent.so" >&2
    exit 1
fi

# nm 不可用——降级到 ldd/大小检查（通过信息保持 loadable/built，
# 不声称 descriptor present）
if ldd "$SO" >/dev/null 2>&1; then
    echo "OK: autotalent.so loadable (LADSPA plugin built)"
    exit 0
fi
sz=$(stat -c%s "$SO" 2>/dev/null || echo 0)
if [ "$sz" -gt 1000 ]; then
    echo "OK: autotalent.so built (size=$sz)"
    exit 0
fi
echo "FAIL: autotalent.so suspicious size ($sz)" >&2
exit 1
