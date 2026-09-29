#!/bin/bash
# 消费者测试 — mcl 22-282
# 用法: test_mcl.sh <包内 bin 目录绝对路径>
# 6 项断言，全部离线，真实执行被适配工具（R34）。
# 核心断言 5 是真实 Markov 聚类管线：mcxload 读 abc 加权边表 → mcl
# 膨胀聚类 → 断言两簇结构（{a1,a2,a3} 与 {b1,b2}，先验已知，确定性）。
set -u
BIN="$1"
MCL="$BIN/mcl"
MCXLOAD="$BIN/mcxload"
MCXDUMP="$BIN/mcxdump"
MCX="$BIN/mcx"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS+1)); echo "ok $PASS - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# 1. mcl --version
OUT="$("$MCL" --version 2>&1 | head -1)"
if [ "$OUT" = "mcl 22-282" ]; then ok "mcl --version"; else bad "mcl --version: got [$OUT]"; fi

# 2. mcx --version（矩阵工具组件）
OUT="$("$MCX" --version 2>&1 | head -1)"
if [ "$OUT" = "mcx 22-282" ]; then ok "mcx --version"; else bad "mcx --version: got [$OUT]"; fi

# 3. mcxload：abc 加权边表 → 原生 mci
printf 'a1 a2 1.0\na2 a3 1.0\na3 a1 1.0\nb1 b2 1.0\nb2 b1 1.0\n' > "$TMP/t.abc"
"$MCXLOAD" -abc "$TMP/t.abc" -write-tab "$TMP/t.tab" -o "$TMP/t.mci" 2>"$TMP/err3.txt"
RC=$?
if [ $RC -eq 0 ] && [ -s "$TMP/t.mci" ]; then
  ok "mcxload abc→mci"
else
  bad "mcxload abc→mci: rc=$RC, err=$(head -2 "$TMP/err3.txt")"
fi

# 4. tab 标签文件完整（5 个标签均在）
N=0
for lbl in a1 a2 a3 b1 b2; do
  if grep -q "^$lbl\$\|^$lbl[[:space:]]" "$TMP/t.tab" 2>/dev/null \
     || grep -qw "$lbl" "$TMP/t.tab"; then
    N=$((N+1))
  fi
done
if [ "$N" -eq 5 ]; then ok "tab 标签完整"; else bad "tab 标签完整: 仅 $N/5"; fi

# 5. mcl 真实聚类（核心算法）：两簇结构先验已知，顺序不敏感断言
"$MCL" "$TMP/t.mci" -I 1.4 -use-tab "$TMP/t.tab" -o "$TMP/t.cls" 2>"$TMP/err5.txt"
RC=$?
NORM="$(sed '/^[[:space:]]*$/d' "$TMP/t.cls" 2>/dev/null \
  | while IFS= read -r line; do
      printf '%s\n' $line | sort | paste -sd ' ' -
    done | sort)"
EXPECT='a1 a2 a3
b1 b2'
if [ $RC -eq 0 ] && [ "$NORM" = "$EXPECT" ]; then
  ok "mcl 聚类两簇划分"
else
  bad "mcl 聚类: rc=$RC, got [$(echo "$NORM" | tr '\n' '|')] err=$(head -2 "$TMP/err5.txt")"
fi

# 6. mcxdump：tab 标签转储（矩阵组件真实 I/O 管线）
"$MCXDUMP" -imx "$TMP/t.mci" -tab "$TMP/t.tab" > "$TMP/dump.txt" 2>"$TMP/err6.txt"
RC=$?
if [ $RC -eq 0 ] && grep -q "a1" "$TMP/dump.txt" && grep -q "b2" "$TMP/dump.txt"; then
  ok "mcxdump 标签转储"
else
  bad "mcxdump 标签转储: rc=$RC, out=$(head -2 "$TMP/dump.txt" 2>/dev/null)"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
