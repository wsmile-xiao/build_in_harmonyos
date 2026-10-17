#!/bin/sh
# gperf test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_gperf.sh <pkg_dir>
#
# 校验 gperf 工具可用（真实执行 + 真实生成，R34 反空壳）：
#   ① gperf --version 断言版本号 3.3
#   ② 用一个真实 .gperf 输入生成 C 查找代码，断言生成物含预期符号
#      —— 这一步直接对应 eudev 的用法（由 keyboard-keys.txt 生成
#      keyboard-keys-from-name.h），证明工具具备下游所需能力，
#      而不是只能打印版本号
set -eu

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

GPERF="$PKG/bin/gperf"
if [ ! -f "$GPERF" ]; then
    echo "FAIL: bin/gperf missing in $PKG" >&2
    exit 1
fi
if [ ! -x "$GPERF" ]; then
    echo "FAIL: bin/gperf not executable" >&2
    exit 1
fi

EXPECT_VER="3.3"

# ① 版本号
OUT="$("$GPERF" --version 2>&1)" || {
    echo "FAIL: gperf --version 退出非零: $OUT" >&2
    exit 1
}
case "$OUT" in
    *"$EXPECT_VER"*) : ;;
    *) echo "FAIL: gperf --version 未报出 $EXPECT_VER: $(echo "$OUT" | head -1)" >&2; exit 1 ;;
esac
echo "OK: gperf --version → $(echo "$OUT" | head -1)"

# ② 真实生成：构造一个 .gperf 输入（形如 eudev 的 keyboard-keys 用法）
# OHOS 上 /tmp 可能只读，故优先用 TMPDIR，再退回当前目录
_BASE="${TMPDIR:-}"
if [ -z "$_BASE" ] || [ ! -w "$_BASE" ]; then
    _BASE="."
fi
W="$(mktemp -d "${_BASE%/}/gperf-tp-XXXXXX" 2>/dev/null || echo "${_BASE%/}/gperf-tp-$$")"
mkdir -p "$W"
trap 'rm -rf "$W"' EXIT INT TERM

cat > "$W/keys.gperf" <<'GEOF'
struct key { const char* name; unsigned short id; };
%null-strings
%%
up, 1
down, 2
left, 3
right, 4
GEOF

if ! "$GPERF" -L ANSI-C -t -N lookup_key -H hash_key_name -C "$W/keys.gperf" > "$W/keys.h" 2>"$W/err.log"; then
    echo "FAIL: gperf 生成失败: $(cat "$W/err.log" 2>/dev/null | head -3)" >&2
    exit 1
fi

# 断言生成物含 gperf 应产出的真实符号/结构（证明确实生成了完美哈希查找表）
for sym in lookup_key hash_key_name; do
    if ! grep -q "$sym" "$W/keys.h" 2>/dev/null; then
        echo "FAIL: 生成物缺少预期符号 '$sym'" >&2
        exit 1
    fi
done
# 断言关键字被编入
if ! grep -q '"up"' "$W/keys.h" 2>/dev/null; then
    echo "FAIL: 生成物未编入关键字 'up'" >&2
    exit 1
fi
SIZE=$(wc -c < "$W/keys.h" 2>/dev/null)
echo "OK: 由 .gperf 生成 C 查找表成功（$SIZE 字节，含 lookup_key/hash_key_name 与关键字）"

echo "gperf test_package PASS ($EXPECT_VER)"
exit 0
