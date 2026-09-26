#!/bin/sh
# test_package 消费者脚本 — coinor-cbc 2.10.13
# 用法：test_cbc.sh <cbc 二进制路径> <可写工作目录>
# 模型：max 3x+2y, s.t. x+y<=4.5, x,y∈{0..3} 整数（General 段声明整数性——
#   LP 格式变量默认连续，不声明会被当纯 LP 求解，走不到 MIP 分支路径）
#   LP 松弛最优 12 @ (3,1.5) → 必须分支；MIP 最优 11 @ (3,1)
# 断言：① 版本横幅 2.10.13 ② "Result - Optimal solution found"（分支后 MIP 终态）
#       ③ Objective value 11（真实求解正确性）
set -eu

CBC_BIN="$1"
WORKDIR="${2:-$PWD}"
cd "$WORKDIR"

cat > model.lp <<'EOF'
\ test_package consumer model for coinor-cbc 2.10.13
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

echo "== test_package: run cbc on model.lp =="
OUT="$("$CBC_BIN" model.lp -solve 2>&1)"
echo "$OUT"

echo "== assertions =="
echo "$OUT" | grep -q "Welcome to the CBC MILP Solver" \
  || { echo "FAIL: missing cbc banner"; exit 1; }
echo "$OUT" | grep -q "Version: 2.10.13" \
  || { echo "FAIL: version banner != 2.10.13"; exit 1; }
echo "$OUT" | grep -q "Result - Optimal solution found" \
  || { echo "FAIL: MIP not solved to optimality (no branching result)"; exit 1; }
echo "$OUT" | grep "Objective value:" | grep -q "11" \
  || { echo "FAIL: objective != 11 (expected x=3,y=1)"; exit 1; }

echo "TEST_PACKAGE PASS: cbc 2.10.13 branched and solved model.lp optimally (objective 11)"
