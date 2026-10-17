#!/bin/bash
# Verify the packaged abiword-plugin-pdf plugin .so: valid ELF with ABI symbols.
# Usage: test_pdf.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

# Locate pdf plugin .so (keep full path)
SO=""
PLUGIN_DIR="$PKG_FOLDER/lib/abiword/plugins"
if [ -d "$PLUGIN_DIR" ]; then
    SO=$(find "$PLUGIN_DIR" -maxdepth 1 -name '*pdf*.so' 2>/dev/null | head -1)
fi
if [ -z "$SO" ]; then
    SO=$(find "$PKG_FOLDER" -name '*pdf*.so*' 2>/dev/null | head -1)
fi
if [ -z "$SO" ]; then
    echo "ERROR: PDF plugin .so not found in package"
    exit 1
fi
echo "  [ok] plugin .so found: $SO"

# readelf: verify ELF + exported ABI symbols (hnp toolchain readelf preferred)
# 注意: 裸名称候选不能用 [ -x "readelf" ]——那只检查当前目录, 不搜索 $PATH。
# 先试 HNP 工具链绝对路径([ -x ] 合适), 再 fallback 到 command -v 搜索 PATH
# (系统 /usr/bin/readelf 等), 否则 HNP 无 readelf 时即使系统可用也会误报。
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then
        READELF="$cand"
        break
    fi
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
if [ -z "$READELF" ]; then
    echo "ERROR: readelf not found (HNP toolchain or PATH)"
    exit 1
fi
echo "  [ok] readelf: $READELF"

# readelf: 用 --dyn-syms(动态导出符号表 .dynsym)校验 ABI 符号——
# -sW 读的是 .symtab 完整符号表(含本地/静态符号, strip 后还可能消失),
# 无法拦截"插件符号未被动态导出、运行时 dlopen 失败"的回归(审查 P2,
# 门禁假阳性)。--dyn-syms -W 等价 -sW 的宽格式但只统计动态导出符号。
OUT=$($READELF --dyn-syms -W "$SO" 2>/dev/null) || { echo "ERROR: readelf failed"; exit 1; }

for sym in abi_plugin_register abi_plugin_unregister abi_plugin_supports_version; do
    if echo "$OUT" | grep -q "$sym"; then
        echo "  [ok] exported symbol: $sym"
    else
        echo "ERROR: expected symbol not found: $sym"
        exit 1
    fi
done

# Count FUNC symbols
func_count=$(echo "$OUT" | awk '$4=="FUNC"' | wc -l)
echo "  [ok] $func_count FUNC symbols exported"

echo "=== Results: 5 passed, 0 failed ==="
exit 0
