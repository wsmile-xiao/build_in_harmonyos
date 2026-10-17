#!/data/service/hnp/bin/bash
# harness-recheck.sh — 第 3 棒改后复跑（只读复核，不改任何导出件）
#   A) 改后的 test.sh 在 CPU 负载下同臂连跑 4 轮（分母仍是 9）
#   B) 加负载两跑：原始 cmp 与"仅掩 Time 字段"后的 cmp
#   C) 正对照排除面的合成反例：同一对文本在第 13 行同时改 dead-ends 计数与 Time 值，
#      旧的行级整行排除 vs 新的字段级排除，各自的"未处置差异"字节数
# 取数环境：B 机（HarmonyOS aarch64），cwd=test_package，. ./conanrun.sh，与
# 2026-09-25 18:59 那轮 fixcheck.sh 同臂。输出随 PR 落 harness-recheck.log。
set -u
export PATH="$HOME/usr/local/bin:$HOME/.local/bin:$PATH"
WT="$HOME/qzy/主理-45-ries-2018.08.05"
T="$WT/archives/r/ries/2018.08.05/test_package"
C="$HOME/tmp/uc2/z45-ries-b3/recheck.$$"
mkdir -p "$C"
cd "$T" || exit 9
. ./conanrun.sh
BIN="$(command -v ries)"
echo "ries on PATH: $BIN"
echo "test.sh sha256: $(sha256sum "$T/test.sh" | cut -d' ' -f1)"

MASK='s/Time:[[:space:]]*[0-9][0-9.]*/Time: <elapsed>/'

pids=""
i=0
while [ "$i" -lt 6 ]; do
  ( while : ; do : ; done ) &
  pids="$pids $!"
  i=`expr $i + 1`
done
sleep 1

echo "=== A) 改后 test.sh，6 枚 spinner 负载下 4 轮 ==="
r=1
while [ "$r" -le 4 ]; do
  bash "$T/test.sh" > "$C/run$r.log" 2>&1; rc=$?
  s=`grep -o 'total=[0-9]* passed=[0-9]* failed=[0-9]*' "$C/run$r.log" | tail -1`
  a9=`grep -E '^\[test\] (PASS|FAIL) -n3' "$C/run$r.log" | tail -1`
  printf 'round %d rc=%d %s :: %s\n' "$r" "$rc" "$s" "$a9"
  r=`expr $r + 1`
done
for p in $pids; do kill "$p" 2>/dev/null; done
sleep 1

echo "=== B) 加负载两跑的原始/掩码 cmp ==="
"$BIN" -n3 2.5063 > "$C/la.txt" 2>&1
"$BIN" -n3 2.5063 > "$C/lb.txt" 2>&1
grep -o 'Time: [0-9.]*' "$C/la.txt" "$C/lb.txt"
cmp -s "$C/la.txt" "$C/lb.txt"; echo "raw cmp rc = $?"
sed -E "$MASK" "$C/la.txt" > "$C/la.m"; sed -E "$MASK" "$C/lb.txt" > "$C/lb.m"
cmp -s "$C/la.m" "$C/lb.m"; echo "masked cmp rc = $?"

echo "=== C) 排除面合成反例（第 13 行同时改 dead-ends 与 Time） ==="
"$BIN" -n3 2.5063 > "$C/a.txt" 2>&1
sed -E 's/^(.*dead-ends:)[[:space:]]*[0-9]+/\1        9999999/' "$C/a.txt" \
  | sed -E 's/Time:[[:space:]]*[0-9][0-9.]*/Time: 0.999/' > "$C/b.txt"
echo "--- 两臂第 13 行原文 ---"
awk 'NR==13' "$C/a.txt"; awk 'NR==13' "$C/b.txt"
echo "--- raw diff ---"
diff "$C/a.txt" "$C/b.txt"
sed -E "$MASK" "$C/a.txt" > "$C/am.txt"; sed -E "$MASK" "$C/b.txt" > "$C/bm.txt"
echo "--- 旧：行级整行排除 diff a b | grep -vE '...|Time: ' ---"
diff "$C/a.txt" "$C/b.txt" \
  | grep -vE '^([0-9]+[acd][0-9]+|---)$|Time: ' > "$C/old.un"
printf 'old undisposed bytes = %s  (0 = 正对照对同行非时钟差异是盲的)\n' "$(wc -c < "$C/old.un")"
echo "--- 新：字段级（同一条 sed 后 diff，只排 hunk 头） ---"
cmp -s "$C/am.txt" "$C/bm.txt"; echo "norm_rc = $?  (1 = 主门禁也判失败)"
diff "$C/am.txt" "$C/bm.txt" \
  | grep -vE '^[0-9]+(,[0-9]+)?[acd][0-9]+(,[0-9]+)?$|^---$' > "$C/new.un"
printf 'new undisposed bytes = %s  (>0 = 抓到了)\n' "$(wc -c < "$C/new.un")"
cat "$C/new.un"
echo RECHECKDONE
