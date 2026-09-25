#!/bin/sh
# test_package 消费者脚本 — coinor-symphony 5.7.2
# 用法：test_symphony.sh <symphony 二进制路径> <可写工作目录>（一律绝对路径）
# 模型：max 3x+2y, s.t. x+y<=4.5, x,y∈{0..3} 整数（General 段声明整数性——
#   LP 格式变量默认连续，不声明会被当纯 LP 求解，走不到 MIP 分支路径）
#   LP 松弛最优 12 @ (3,1.5) → 必须分支；MIP 最优 11 @ (3,1)
# 输入格式：-L 读 LP（-F 是 MPS——探索实测 -F 收 LP 文件报
#   "Errors in reading mps file" 退出 -122）
# 断言：① 求解器横幅 ② Version: 5.7.2 ③ Optimal Solution Found
#       ④ Solution Cost: -11.0000000000（最大化被改写为最小化，Coin0009I 自报）
set -eu

SYMPHONY_BIN="$1"
WORKDIR="${2:-$PWD}"
cd "$WORKDIR"

cat > model.lp <<'EOF'
\ test_package consumer model for coinor-symphony 5.7.2
Maximize
 obj: 3 x + 2 y
Subject To
 c1: x + y <= 4.5
Bounds
 x <= 3
 y <= 3
General
 x y
End
EOF

echo "== test_package: run symphony -L model.lp =="
OUT="$("$SYMPHONY_BIN" -L model.lp 2>&1)"
echo "$OUT"

echo "== assertions =="
echo "$OUT" | grep -q "Welcome to the SYMPHONY MILP Solver" \
  || { echo "FAIL: missing symphony banner"; exit 1; }
echo "$OUT" | grep -q "Version: 5.7.2" \
  || { echo "FAIL: version banner != 5.7.2"; exit 1; }
echo "$OUT" | grep -q "Optimal Solution Found" \
  || { echo "FAIL: MIP not solved to optimality"; exit 1; }
echo "$OUT" | grep -q "Solution Cost: -11.0000000000" \
  || { echo "FAIL: objective != -11 (max 3x+2y, expected x=3,y=1)"; exit 1; }

echo "TEST_PACKAGE PASS: symphony 5.7.2 branched and solved model.lp optimally (objective 11)"
