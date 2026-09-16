#!/bin/sh
# run_mrc_tests.sh — mrc 消费者功能测试（真实执行被测二进制）
#
# 背景：本包 test_package 原先只有一个 conanfile.py，缺少 CI 门禁 L0c 要求的
# 测试源文件（.c/.cpp/.cc/.cxx/.sh/.py）。本脚本即为该测试源，同时把原先
# "只校验产物非空" 的弱断言**加强为对产物内容的真实校验**（R34）。
#
# 校验项：
#   1. mrc 能成功生成对象文件（退出码 0）
#   2. 产物非空
#   3. 产物是 **ELF relocatable（AArch64）** —— 而非任意文本文件
#   4. 产物内嵌了源资源的**载荷文本**（证明资源内容真的被编译进去）
#   5. 产物导出了 mrc 约定的 **gResource 符号**（gResourceData/Name/Index）
#      —— 这些正是消费者程序 include mrc 生成头文件后要引用的符号
#
# 用法: run_mrc_tests.sh <mrc_bin> <resource_file> <out_dir>
# 退出码: 0 全通过; 1 有失败
set -u

MRC_BIN="${1:?usage: run_mrc_tests.sh <mrc_bin> <resource_file> <out_dir>}"
RSRC="${2:?missing resource file}"
OUT_DIR="${3:?missing output dir}"

mkdir -p "$OUT_DIR"
OBJ="$OUT_DIR/hello-rsrc.obj"

PASS=0
FAIL=0

ok()   { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
bad()  { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "== mrc 消费者功能测试 =="
echo "   bin=$MRC_BIN"
echo "   rsrc=$RSRC"
echo "   out=$OBJ"

# ── 1. mrc 能成功生成对象文件 ──
if "$MRC_BIN" -o "$OBJ" "$RSRC" >/dev/null 2>&1; then
    ok "mrc 执行成功（退出码 0）"
else
    bad "mrc 执行失败"
    echo "RESULT: passed=$PASS failed=$FAIL"
    exit 1
fi

# ── 2. 产物存在且非空 ──
if [ -s "$OBJ" ]; then
    ok "产物非空（$(wc -c < "$OBJ" | tr -d ' ') 字节）"
else
    bad "产物不存在或为空"
    echo "RESULT: passed=$PASS failed=$FAIL"
    exit 1
fi

# ── 3. 产物是 ELF relocatable / AArch64 ──
if command -v readelf >/dev/null 2>&1; then
    HDR=$(readelf -h "$OBJ" 2>/dev/null || true)
    case "$HDR" in
        *"REL (Relocatable file)"*) ok "产物为 ELF relocatable" ;;
        *) bad "产物不是 ELF relocatable" ;;
    esac
    case "$HDR" in
        *AArch64*) ok "产物架构为 AArch64" ;;
        *) bad "产物架构不是 AArch64" ;;
    esac
else
    echo "  [SKIP] readelf 不可用，跳过 ELF 头校验（环境限制，不计为通过）"
fi

# ── 4. 内嵌了资源载荷文本（证明内容真被编译进去）──
# 取资源文件首行的一个稳定的词做探针，避免整行空白的干扰
PROBE=$(sed -n '1p' "$RSRC" 2>/dev/null | tr -d '\r' | cut -c1-20)
if [ -n "$PROBE" ] && strings "$OBJ" 2>/dev/null | grep -Fq "$PROBE"; then
    ok "产物内嵌资源载荷文本（探针: \"$PROBE\"）"
else
    bad "产物中未找到资源载荷文本（探针: \"$PROBE\"）"
fi

# ── 5. 导出 mrc 约定的 gResource 符号 ──
SYMS=$(strings "$OBJ" 2>/dev/null | tr '\n' ' ')
MISSING=""
for s in gResourceIndex gResourceData gResourceName; do
    case "$SYMS" in
        *"$s"*) ;;
        *) MISSING="$MISSING $s" ;;
    esac
done
if [ -z "$MISSING" ]; then
    ok "产物导出 gResource 符号（gResourceIndex/Data/Name）"
else
    bad "产物缺少 gResource 符号:$MISSING"
fi

echo "RESULT: passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
