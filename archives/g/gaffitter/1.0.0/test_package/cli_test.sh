#!/usr/bin/env bash
# test_package/cli_test.sh — gaffitter (可执行名 fit) CLI 真实行为测试
# 在 conanrun 环境运行（PATH 含安装的 bin/）
# 覆盖：版本/帮助/错误路径退出码、管道直输、顺序切分、超大条目排除、
#       恰好装满、--bins 截断、GA 容量守恒与理论最优、真实文件 stat 装箱、
#       管道文件名输入（find/ls 集成语义）
set -u

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS $PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL $FAIL: $1"; }
rc_is() { # 描述 期望码 实际码
  if [ "$3" -eq "$2" ]; then ok "$1 (rc=$3)"; else bad "$1 (rc=$3, want $2)"; fi
}
has() { # 描述 被检文本 子串
  case "$2" in
    *"$3"*) ok "$1" ;;
    *) bad "$1 (未找到: $3)" ;;
  esac
}

command -v fit >/dev/null 2>&1 || { echo "FATAL: fit not on PATH"; exit 1; }

# ---------- 1. 基础：--version / -h ----------
OUT=$(fit --version 2>&1); RC=$?
rc_is "--version 退出码" 0 "$RC"
if [ "$(echo "$OUT" | head -1)" = "gaffitter 1.0.0 (Genetic Algorithm File Fitter) (C) 2005-2015" ]; then
  ok "--version 精确版本串"
else
  bad "--version 版本串不符: $(echo "$OUT" | head -1)"
fi

OUT=$(fit -h 2>&1); RC=$?
rc_is "-h 退出码" 0 "$RC"
has "-h 用法行" "$OUT" "Usage: fit -t target[unit]"

# ---------- 2. 错误路径退出码（上游语义：CmdLine 异常=1，输入异常=2）----------
OUT=$(fit -t 2>&1); RC=$?
rc_is "-t 缺值退出码 (CmdLine 异常)" 1 "$RC"
has "-t 缺值错误信息" "$OUT" "value was not provided"

OUT=$(fit --di "60 a" 2>&1); RC=$?
rc_is "缺 --target 退出码" 2 "$RC"
has "缺 --target 错误信息" "$OUT" "Missing '--target'"

OUT=$(fit -t 100 --di < /dev/null 2>&1); RC=$?
rc_is "空输入退出码" 2 "$RC"
has "空输入错误信息" "$OUT" "No input to process"

# ---------- 3. 管道直输模式（--di）+ 顺序切分（--sp，确定性）----------
OUT=$(printf '%s\n' "60 a" "30 b" "50 c" "20 d" | fit - --di -t 100 --sp --ss 2>&1); RC=$?
rc_is "管道直输 --sp 退出码" 0 "$RC"
has "卷1 摘要 (a60+b30=90≤100)" "$OUT" "[1] 90/100 of 160, Diff: 10, Items: 2/4"
has "卷2 摘要 (c50+d20=70≤100)" "$OUT" "[2] 70/100 of 160, Diff: 30, Items: 2/4"
has "卷1 条目 a --ss 显示大小" "$OUT" "$(printf 'a\t60')"
has "卷1 条目 b --ss 显示大小" "$OUT" "$(printf 'b\t30')"
has "卷2 条目 c --ss 显示大小" "$OUT" "$(printf 'c\t50')"
has "卷2 条目 d --ss 显示大小" "$OUT" "$(printf 'd\t20')"

# ---------- 4. 超大条目：大于 target 的条目被排除并告警 ----------
OUT=$(fit --di -t 100 --sp --ss "150 big" "50 s" 2>&1); RC=$?
rc_is "超大条目场景退出码" 0 "$RC"
has "超大条目排除告警" "$OUT" "bigger than 'target'(100): big (150)"
has "剩余条目装箱摘要" "$OUT" "[1] 50/100 of 50, Diff: 50, Items: 1/1"

# ---------- 5. 恰好装满 ----------
OUT=$(fit --di -t 100 --sp --ss "100 exact" 2>&1); RC=$?
rc_is "恰好装满退出码" 0 "$RC"
has "恰好装满摘要 (100/100, Diff 0)" "$OUT" "[1] 100/100 of 100, Diff: 0, Items: 1/1"

# ---------- 6. --bins 限制输出卷数 ----------
OUT=$(fit --di -t 100 --bins 1 --sp --ss "60 a" "30 b" "50 c" "20 d" 2>&1); RC=$?
rc_is "--bins 1 退出码" 0 "$RC"
if echo "$OUT" | grep -qF "[1] 90/100 of 160" && ! echo "$OUT" | grep -qF "[2]"; then
  ok "--bins 1 仅输出一卷"
else
  bad "--bins 1 输出异常: $OUT"
fi

# ---------- 7. GA 模式：容量约束 + 守恒 + 理论最优 + 固定种子确定性 ----------
GA1=$(fit --di -t 100 "60 a" "30 b" "50 c" "20 d" 2>&1); RC=$?
rc_is "GA 退出码" 0 "$RC"
re='^\[[0-9]+\] ([0-9]+)/100 of 160,'
SUMS=()
while IFS= read -r line; do
  if [[ $line =~ $re ]]; then SUMS+=("${BASH_REMATCH[1]}"); fi
done <<< "$GA1"
ALL_LE=1; TOTAL=0
for s in ${SUMS[@]+"${SUMS[@]}"}; do
  [ "$s" -le 100 ] || ALL_LE=0
  TOTAL=$((TOTAL + s))
done
if [ "$ALL_LE" -eq 1 ] && [ "${#SUMS[@]}" -gt 0 ]; then
  ok "GA 每卷 ≤ target (容量约束)"
else
  bad "GA 存在超容量卷: ${SUMS[*]:-none}"
fi
if [ "$TOTAL" -eq 160 ]; then
  ok "GA 容量守恒 (Σ卷和=160=Σ条目)"
else
  bad "GA 容量不守恒: Σ=$TOTAL"
fi
if [ "${#SUMS[@]}" -eq 2 ]; then
  ok "GA 卷数=理论最优 2 (⌈160/100⌉)"
else
  bad "GA 卷数=${#SUMS[@]}, 非理论最优"
fi
GA2=$(fit --di -t 100 "60 a" "30 b" "50 c" "20 d" 2>&1)
if [ "$GA1" = "$GA2" ]; then
  ok "GA 固定种子确定性 (两次运行一致)"
else
  bad "GA 两次运行不一致"
fi

# ---------- 8. --ga-theo：达到理论最优即停 ----------
OUT=$(fit --di -t 100 --ga-theo --ss "60 a" "30 b" "50 c" "20 d" 2>&1); RC=$?
rc_is "--ga-theo 退出码" 0 "$RC"
has "--ga-theo 卷1 摘要" "$OUT" "[1] 80/100 of 160, Diff: 20, Items: 2/4"
has "--ga-theo 卷2 摘要" "$OUT" "[2] 80/100 of 160, Diff: 20, Items: 2/4"

# ---------- 9. 真实文件模式（DiskUsage.cc 的 stat/lstat 路径）----------
FIX="$PWD/_fit_fixtures"
rm -rf "$FIX"; mkdir -p "$FIX"
dd if=/dev/zero of="$FIX/f1.bin" bs=1024 count=60 status=none
dd if=/dev/zero of="$FIX/f2.bin" bs=1024 count=30 status=none
dd if=/dev/zero of="$FIX/f3.bin" bs=1024 count=50 status=none
OUT=$(fit -t 100k --ss "$FIX/f1.bin" "$FIX/f2.bin" "$FIX/f3.bin" 2>&1); RC=$?
rc_is "文件模式退出码 (stat 真实文件)" 0 "$RC"
has "文件模式 卷1 摘要 (60+30KiB)" "$OUT" "[1] 90.00KiB/100.00KiB of 140.00KiB, Diff: 10.00KiB, Items: 2/3"
has "文件模式 卷2 摘要 (50KiB)" "$OUT" "[2] 50.00KiB/100.00KiB of 140.00KiB, Diff: 50.00KiB, Items: 1/3"
for f in f1.bin f2.bin f3.bin; do
  if echo "$OUT" | grep -qF "$f"; then
    ok "文件模式 stat 到 $f (名字保留)"
  else
    bad "文件模式输出未含 $f"
  fi
done

# ---------- 10. 管道文件名输入（find/ls | fit - 集成语义）----------
OUT=$(cd "$FIX" && ls | fit - -t 100k --sp --ss 2>&1); RC=$?
rc_is "管道文件名退出码" 0 "$RC"
has "管道文件名 卷1 摘要" "$OUT" "[1] 90.00KiB/100.00KiB of 140.00KiB, Diff: 10.00KiB, Items: 2/3"

rm -rf "$FIX"
TOTAL_N=$((PASS + FAIL))
echo ""
echo "CLI-TEST: $PASS/$TOTAL_N assertions passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
  echo "CLI-TEST-OK"
else
  echo "CLI-TEST-FAILED"
  exit 1
fi
