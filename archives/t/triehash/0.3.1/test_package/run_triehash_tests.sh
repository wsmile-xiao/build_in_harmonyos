#!/bin/sh
# run_triehash_tests.sh — triehash 消费者功能测试（真实执行被测脚本）
#
# 本脚本同时承担两个职责：
#   ① 满足 CI 门禁 L0c 对 test_package/ 下「测试源文件」的要求（.sh）
#   ② 对 triehash 做**真实功能验证**（R34），而非仅检查文件存在
#
# 断言（6 项）：
#   1. 可执行且 --help 正常退出
#   2. 正常路径：由关键字生成非空 .h
#   3. 正常路径：生成非空 .c
#   4. 头文件内容真实：含 enum 与输入关键字
#   5. -C -（标准输出）可用
#   6. 负向：不存在的输入文件应失败（退出码非 0）
#
# 用法: run_triehash_tests.sh <triehash_bin> <out_dir>
# 退出码: 0 全通过; 1 有失败
set -u

TRIEHASH="${1:?usage: run_triehash_tests.sh <triehash_bin> <out_dir>}"
OUT_DIR="${2:?missing output dir}"

mkdir -p "$OUT_DIR"
IN="$OUT_DIR/keywords.txt"
H="$OUT_DIR/trie.h"
C="$OUT_DIR/trie.c"

PASS=0
FAIL=0
ok()  { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
bad() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "== triehash 消费者功能测试 =="
echo "   bin=$TRIEHASH"
echo "   out=$OUT_DIR"

# 输入关键字（triehash 每行一个）
printf 'apple\nbanana\ncherry\ndate\nelderberry\n' > "$IN"

# ── 1. 可执行 + --help ──
if "$TRIEHASH" --help >/dev/null 2>&1; then
    ok "triehash --help 正常退出"
else
    # 部分版本 --help 返回非 0，但应至少能打印用法；做一次宽松判定
    if "$TRIEHASH" --help 2>&1 | grep -qi "usage"; then
        ok "triehash --help 输出用法说明"
    else
        bad "triehash --help 不可用"
    fi
fi

# ── 2/3. 正常路径生成 .h 与 .c ──
"$TRIEHASH" -C "$C" -H "$H" "$IN" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$H" ]; then
    ok "生成非空 .h（$(wc -c < "$H" | tr -d ' ') 字节）"
else
    bad "未生成 .h（rc=$rc）"
fi

if [ -s "$C" ]; then
    ok "生成非空 .c（$(wc -c < "$C" | tr -d ' ') 字节）"
else
    bad "未生成 .c"
fi

# ── 4. 头文件内容真实：含 enum 与输入关键字 ──
if [ -s "$H" ]; then
    if grep -q "enum" "$H" && grep -q "apple" "$H"; then
        ok "头文件含 enum 与关键字（内容真实）"
    else
        bad "头文件缺少 enum 或关键字"
    fi
else
    bad "头文件为空，跳过内容校验"
fi

# ── 5. -C -（标准输出）可用 ──
if "$TRIEHASH" -C - -H "$H" "$IN" 2>/dev/null | grep -q "enum"; then
    ok "-C -（标准输出）可用"
else
    bad "-C - 未输出预期内容"
fi

# ── 6. 负向：不存在的输入文件应失败 ──
if "$TRIEHASH" -C "$OUT_DIR/x.c" -H "$OUT_DIR/x.h" "$OUT_DIR/does-not-exist.txt" >/dev/null 2>&1; then
    bad "不存在的输入文件竟然成功（应失败）"
else
    ok "不存在的输入文件正确失败"
fi

echo "RESULT: passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
